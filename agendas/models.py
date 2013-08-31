from __future__ import division

from itertools import chain
from operator import attrgetter, itemgetter
from collections import defaultdict
import math

from django.db import connection
from django.db import models
from django.db.models import Sum, Q, Count, F
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.conf import settings

from django.contrib.auth.models import User
from laws.models import VoteAction, Vote

from mks.models import Member, Knesset
import queries

AGENDAVOTE_SCORE_CHOICES = (
    ('', _("Not selected")),
    (-1.0, _("Opposes fully")),
    (-0.5, _("Opposes partially")),
    (0.0, _("Agnostic")),
    (0.5, _("Complies partially")),
    (1.0, _("Complies fully")),
)
IMPORTANCE_CHOICES = (
    ('', _("Not selected")),
    (0.0, _("Marginal Importance")),
    (0.3, _("Medium Importance")),
    (0.6, _("High Importance")),
    (1.0, _("Very High Importance")),
)

class UserSuggestedVote(models.Model):
    agenda = models.ForeignKey('Agenda', related_name='user_suggested_votes')
    vote = models.ForeignKey('laws.Vote', related_name='user_suggested_agendas')
    reasoning = models.TextField(blank=True, default='')
    user = models.ForeignKey(User, related_name='suggested_agenda_votes')
    sent_to_editor = models.BooleanField(default=False)

    class Meta:
        unique_together = ('agenda', 'vote', 'user')

class AgendaVoteManager(models.Manager):
    db_month_trunc_functions = {
        'sqlite3':{'monthfunc':"strftime('%%Y-%%m-01'", 'nowfunc':'date()'},
        'postgresql_psycopg2':{'monthfunc':"date_trunc('month'", 'nowfunc':'now()'}
    }

    def compute_all(self):
        db_engine = settings.DATABASES['default']['ENGINE']
        db_functions = self.db_month_trunc_functions[db_engine.split('.')[-1]]
        agenda_query = queries.BASE_AGENDA_QUERY % db_functions
        cursor = connection.cursor()
        cursor.execute(agenda_query)

        mk_query = queries.BASE_MK_QUERY % db_functions
        cursor.execute(mk_query)

class Scorable(models.Model):
    score = models.FloatField(default=0.0, choices=AGENDAVOTE_SCORE_CHOICES)
    reasoning = models.TextField(null=True)

    def get_score_header(self):
        return _('Position')
    
    def update(self, details):
        self.score = details['weight']
        self.reasoning = details['reasoning']

    class Meta:
        abstract = True

class Important(Scorable):
    importance = models.FloatField(default=1.0, choices=IMPORTANCE_CHOICES)

    def get_importance_header(self):
        return _('Importance')

    def update(self, details):
        self.importance = details['importance']
        super(Important, self).update(details)
        
    class Meta:
        abstract = True
   
from listeners import Listener, Follower

@Listener()
class AgendaVote(Important):
    agenda = models.ForeignKey('Agenda', related_name='agendavotes')
    vote = models.ForeignKey('laws.Vote', related_name='agendavotes')

    objects = AgendaVoteManager()

    def detail_view_url(self):
        return reverse('agenda-vote-detail', args=[self.pk])

    @property
    def key(self):
        return self.vote

    @staticmethod
    def keyname():
        return 'vote'
    
    def get_importance_header(self):
        return _('Importance')

    class Meta:
        unique_together = ('agenda', 'vote')

    def __unicode__(self):
        return u"{} {}".format(self.agenda, self.vote)

    def update_monthly_counters(self):
        agendaScore = float(self.score) * float(self.importance)
        objMonth = dateMonthTruncate(self.vote.time)

        summaryObjects = SummaryAgenda.objects.filter(agenda=self.agenda,  month=objMonth).all()
#        <<<<<<< HEAD
        agendasByMk = [s.mk_id for s in summaryObjects if s.summary_type != 'AG']
#         =======
#         agendaSummary   = None
#         if not filter(lambda summary:summary.summary_type=='AG',summaryObjects):
#             agendaSummary   = SummaryAgenda(month=objMonth,
#                                             agenda=self.agenda,
#                                             summary_type='AG',
#                                             score=abs(agendaScore),
#                                             votes=1)
#         else:
#             existingAgenda = filter(lambda summary:summary.summary_type=='AG',summaryObjects)[0]
#             existingAgenda.votes += 1
#             existingAgenda.score += abs(agendaScore)
#             existingAgenda.save()
# 
#         agendasByMk     = dict(map(lambda summary:(summary.mk_id,summary),
#                                    filter(lambda summary:summary.summary_type=='MK',
#                                           summaryObjects)))
# >>>>>>> 4b160480cb5b568e1be245905f8a384732e39d61
        newObjects = []
        if len(agendasByMk) == len(summaryObjects):
            newObjects.append(SummaryAgenda(agenda=self.agenda, month=objMonth,  votes=1,
                                            summary_type='AG',   score=agendaScore))

        voters = defaultdict(list)
        for voteaction in self.vote.voteaction_set.all():
            if voteaction.member_id in agendasByMk:
                voters[voteaction.type].append(voteaction.member_id)
            else:
                newObjects.append(SummaryAgenda(agenda=self.agenda, month=objMonth,  votes=1,
                                            summary_type='MK',   mk_id=voteaction.member_id,
                                            score=agendaScore * (1 if voteaction.type == 'for' else -1)))
        fvotes = F('votes') + 1
        SummaryAgenda.objects.filter(mk_id__in=voters['for']).update(votes=fvotes, score=F('score') + agendaScore)
        SummaryAgenda.objects.filter(mk_id__in=voters['against']).update(votes=fvotes, score=F('score') - agendaScore)
        if newObjects:
            SummaryAgenda.objects.bulk_create(newObjects)

    def save(self, *args, **kwargs):
        super(AgendaVote, self).save(*args, **kwargs)
        self.update_monthly_counters()

@Listener()
class AgendaMeeting(Scorable):
    agenda = models.ForeignKey('Agenda', related_name='agendameetings')
    meeting = models.ForeignKey('committees.CommitteeMeeting',
                                related_name='agendacommitteemeetings')

    @property
    def key(self):
        return self.meeting

    @staticmethod
    def keyname():
        return 'meeting'

    def detail_view_url(self):
        return reverse('agenda-meeting-detail', args=[self.pk])

    def get_score_header(self):
        return _('Importance')
    
    def get_importance_header(self):
        return ''

    class Meta:
        unique_together = ('agenda', 'meeting')

    def __unicode__(self):
        return u"{} {}".format(self.agenda, self.meeting)

@Listener()
class AgendaBill(Important):
    agenda = models.ForeignKey('Agenda', related_name='agendabills')
    bill = models.ForeignKey('laws.bill', related_name='agendabills')

    @property
    def key(self):
        return self.bill

    @staticmethod
    def keyname():
        return 'bill'

    def detail_view_url(self):
        return reverse('agenda-bill-detail', args=[self.pk])

    class Meta:
        unique_together = ('agenda', 'bill')

    def __unicode__(self):
        return u"{} {}".format(self.agenda, self.bill)

def get_top_bottom(lst, top, bottom):
    """
    Returns a cropped list, keeping some of the list's top and bottom.
    Edge conditions are handled gracefuly.
    Input list should be ascending so that top is at the end.
    """
    if len(lst) < top + bottom:
        delta = top + bottom - len(lst)
        x = int(math.floor(delta / 2))
        bottom -= x 
        top -= x + delta % 2
    return {'top': lst[-top:] if top else [],
            'bottom': lst[:bottom]}

class AgendaManager(models.Manager):

    def get_selected_for_instance(self, instance, user=None, top=3, bottom=3):
        # Returns interesting agendas for model instances such as: member, party
        agendas = list(self.get_relevant_for_user(user))
        for agenda in agendas:
            agenda.score = getattr(agenda, '{}_score'.format(type(instance).__name__.lower()))(instance)
            agenda.significance = agenda.score * agenda.num_followers
        agendas.sort(key=attrgetter('significance'))
        agendas = get_top_bottom(agendas, top, bottom)
        agendas['top'].sort(key=attrgetter('score'), reverse=True)
        agendas['bottom'].sort(key=attrgetter('score'), reverse=True)
        return agendas['top'] + agendas['bottom']

    def get_relevant_for_mk(self, mk, agendaId):
        return AgendaVote.objects.filter(agenda__id=agendaId, vote__votes__id=mk).distinct()
    
    def get_relevant_for_user(self, user):
        def get_priv_type(user):
            if user is None or not user.is_authenticated(): return 0
            elif user.is_superuser:  return 1
            else: return 2   
        t = get_priv_type(user)
        if   t == 0: agendas = Agenda.objects.filter(is_public=True)
        elif t == 1: agendas = Agenda.objects.all()
        elif t == 2: agendas = Agenda.objects.filter(Q(is_public=True) | Q(editors=user))
        
        agendas = agendas.order_by('-num_followers').prefetch_related('agendavotes')
        
        if t == 2:
            return agendas.distinct()
        return agendas

    def get_possible_to_suggest(self, user, vote):
        #FIX: magic return values.
        #should be fixed in the calling code too.
        if user.is_authenticated():
            return Agenda.objects.filter(is_public=True)\
                            .exclude(editors=user)\
                            .exclude(agendavotes__vote=vote)\
                            .distinct()
        return False

    def get_mks_values(self):
        mks_values = cache.get('agendas_mks_values')
        if not mks_values:
            q = queries.agendas_mks_grade()
            # outer join - add missing mks to agendas
            # generates a set of all the current mk ids that have ever voted for any agenda
            # its not perfect, but its better than creating another query to generate all known mkids
            all_mks = {x[0] for x in chain.from_iterable(q.values())}
            mks_values = {}
            for agendaId, agendaVotes in q.items():
                # the newdict will have 0's for each mkid, the update will change the value for known mks
                agenda_mks = set()
                res=[]
                for mkid, score, volume, numvotes in agendaVotes:
                    agenda_mks.add(mkid)
                    res.append( (mkid,(score, volume, numvotes)) )
                res.sort(key=lambda x:x[1][0], reverse=True)
                
                scores = enumerate(chain(res, ((mkid, (0,0,0)) for mkid in all_mks-agenda_mks)), 1)
                mks_values[agendaId] = [(mkid, {'rank':rank, 'score':score, 'volume':volume, 'numvotes':numvotes})
                                         for rank, (mkid, (score, volume, numvotes)) in  scores]
            cache.set('agendas_mks_values', mks_values, 1800)
        return mks_values


    # def get_mks_values(self,ranges=None):
    #     if ranges is None:
    #         ranges = [[None,None]]
    #     mks_values = False
    #     if ranges == [[None,None]]:
    #         mks_values = cache.get('agendas_mks_values')
    #     if not mks_values:
    #         # get list of mk ids
    #         # generate summary query
    #         # query summary
    #         # split data into appropriate ranges
    #         # compute agenda measures per range
    #         #   add missing mks while you're there
    #         q = queries.getAllAgendaMkVotes()
    #         # outer join - add missing mks to agendas
    #         newAgendaMkVotes = {}
    #         # generates a set of all the current mk ids that have ever voted for any agenda
    #         # its not perfect, but its better than creating another query to generate all known mkids
    #         allMkIds = set(map(itemgetter(0),chain.from_iterable(q.values())))
    #         for agendaId,agendaVotes in q.items():
    #             # the newdict will have 0's for each mkid, the update will change the value for known mks
    #             newDict = {}.fromkeys(allMkIds,(0,0,0))
    #             newDict.update(dict(map(lambda (mkid,score,volume,numvotes):(mkid,(score,volume,numvotes)),agendaVotes)))
    #             newAgendaMkVotes[agendaId]=newDict.items()
    #         mks_values = {}
    #         for agenda_id, scores in newAgendaMkVotes.items():
    #             mks_values[agenda_id] = \
    #                 map(lambda x: (x[1][0], dict(score=x[1][1][0], rank=x[0], volume=x[1][1][1], numvotes=x[1][1][2])),
    #                     enumerate(sorted(scores,key=lambda x:x[1][0],reverse=True), 1))
    #         if ranges = [[None,None]]:
    #             cache.set('agendas_mks_values', mks_values, 1800)
    #     return mks_values

    def get_all_party_values(self):
        return queries.getAllAgendaPartyVotes()

@Follower
class Agenda(models.Model):
    name = models.CharField(max_length=200)
    public_owner_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    editors = models.ManyToManyField('auth.User', related_name='agendas')
    votes = models.ManyToManyField('laws.Vote', through=AgendaVote)
    is_public = models.BooleanField(default=False)
    num_followers = models.IntegerField(default=0)
    image = models.ImageField(blank=True, null=True, upload_to='agendas')

    objects = AgendaManager()

    class Meta:
        verbose_name = _('Agenda')
        verbose_name_plural = _('Agendas')
        unique_together = (("name", "public_owner_name"),)

    def __unicode__(self):
        return u"{} {} {}".format(self.name, _('edited by'), self.public_owner_name)

    @models.permalink
    def get_absolute_url(self):
        return ('agenda-detail', [str(self.id)])

    @models.permalink
    def get_edit_absolute_url(self):
        return ('agenda-detail-edit', [str(self.id)])
    
    def calculate_score(self, members):
        # Since we're already calculating python side, no need to do 2 queries
        # with joins, select for and against, and calcualte the things        
        qs = list(AgendaVote.objects.filter(
            agenda=self,
            vote__voteaction__member__in=members,
            vote__voteaction__type__in=['for', 'against']).extra(
                select={'weighted_score':'agendas_agendavote.score * agendas_agendavote.importance'}
            ).values_list('weighted_score', 'vote__voteaction__type'))
        
        total_score = 0
        for score, action_type in qs:
            if action_type == 'against':
                total_score -= score
            else:
                total_score += score
        
        # To save the queries, make sure to pass prefetch/select related
        # Removed the values call, so that we can utilize the prefetched stuf
        # This reduces the number of queries when called for example from
        # AgendaResource.dehydrate        
        max_score = sum(abs(x.score * x.importance) for x in self.agendavotes.all())
        max_score *= len(members)
        return max_score and (total_score * 100.0 / max_score)
         
    def member_score(self, member):
        return self.calculate_score([member])
    
    def party_score(self, party):
        return self.calculate_score(party.members.all())

    def candidate_list_score(self, candidate_list):
        return self.calculate_score(candidate_list.member_ids)
    
    def related_mk_votes(self, member):
        # Find all votes that
        #   1) This agenda is ascribed to
        #   2) the member participated in and either voted for or against
        # for_votes      = AgendaVote.objects.filter(agenda=self,vote__voteaction__member=member,vote__voteaction__type="for").distinct()
        # against_votes   = AgendaVote.objects.filter(agenda=self,vote__voteaction__member=member,vote__voteaction__type="against").distinct()
        voteactions = VoteAction.objects.filter(member=member, vote__agendavotes__agenda=self)
        all_votes = AgendaVote.objects.filter(agenda=self, vote__voteaction__member=member).distinct()
        # TODO: improve ugly code below
        member_votes = list()
        for member_vote in reversed(all_votes):
            for voteaction in voteactions:
                if voteaction.vote == member_vote.vote:
                    member_vote.voteaction = voteaction
                    member_votes.append(member_vote)

        return member_votes
        # return AgendaVote.objects.filter(agenda=self,vote__voteaction__member=mk).distinct()

    def selected_instances(self, cls, top=3, bottom=3):
        instances = list(cls.objects.all())
        for instance in instances:
            instance.score = self.__getattribute__('{}_score'.format(instance.__class__.__name__.lower()))(instance)
        instances.sort(key=attrgetter('score'))
        instances = get_top_bottom(instances, top, bottom)
        instances['top'].sort(key=attrgetter('score'), reverse=True)
        instances['bottom'].sort(key=attrgetter('score'), reverse=True)
        return instances

    def get_mks_totals(self, member):
        "Get count for each vote type for a specific member on this agenda"

        # let's split qs to make it more readable
        qs = VoteAction.objects.filter(member=member, type__in=('for', 'against'), vote__agendavotes__agenda=self)
        qs = list(qs.values('type').annotate(total=Count('id')))

        totals = sum(x['total'] for x in qs)
        qs.append({'type': 'no-vote', 'total': self.votes.count() - totals})

        return qs

    def generate_summary_filters(self, ranges):
        results = Q()
        for gte, lt in ranges:
            queryFields = {}
            if gte:
                queryFields['month__gte'] = gte
            if lt:
                queryFields['month__lt']  = lt
            if not queryFields:
                # might as well not filter at all
                return Q()
            results |= Q(**queryFields)
        return results

    def get_mks_values(self, ranges=((None, None),)):
        fullRange = (None, None) in ranges
        mks_values = fullRange and cache.get('agenda_{}_mks_values'.format(self.id))
        if not mks_values:

            # query summary
            filterList = self.generate_summary_filters(ranges)
            summaries = list(SummaryAgenda.objects.filter(filterList, agenda=self))

            # import pdb; pdb.set_trace()
            # group summaries for respective ranges
            summaries_for_ranges = []
            for gte, lt in ranges:
                summaries_for_range = defaultdict(list)
                for s in summaries:
                    if (not gte or s.month >= gte) and (not lt or s.month < lt ):
                        summaries_for_range[s.summary_type].append(s)
                summaries_for_ranges.append(summaries_for_range)
                

            # get list of mk ids
            mk_ids = Member.objects.all().values_list('id', flat=True)
            # compute agenda measures, store results per MK
            mk_results = { mk_id:[] for mk_id in mk_ids }
            for summaries in summaries_for_ranges:
                agenda_data = summaries['AG']
                total_votes = sum(x.votes for x in agenda_data)
                total_score = sum(x.score for x in agenda_data)
                current_mks_data = indexby(summaries['MK'], attrgetter('id'))
                
                # calculate results per mk
                range_mk_results = []
                for mk_id in mk_ids:
                    mk_data = current_mks_data[mk_id]
                    mk_votes = sum(x.votes for x in mk_data)
                    mk_volume = total_votes and 100*mk_votes / total_votes
                    mk_score = total_score and 100*sum(x.score for x in mk_data) / total_score
                    range_mk_results.append( (mk_id, mk_votes, mk_score, mk_volume) )

                # sort results by score descending
                range_mk_results.sort(key=itemgetter(2, 0), reverse=True)
                for rank, (mk_id, mk_votes, mk_score, mk_volume) in enumerate(range_mk_results):
                    mk_range_data = dict(score=mk_score, rank=rank, volume=mk_volume, numvotes=mk_votes)
                    if fullRange:
                        mk_results[mk_id] = mk_range_data
                    else:
                        mk_results[mk_id].append(mk_range_data)
            if fullRange:
                cache.set('agenda_{}_mks_values'.format(self.id), mks_values, 1800)
        if fullRange:
            mk_results = sorted(mk_results.items(), key=lambda (k, v):v['rank'])
        return mk_results


    def get_mks_values_old(self, knesset_number=None):
        """Return mks values.

        :param knesset_number: The knesset numer of the mks. ``None`` will
                               return current knesset (default: ``None``).
        """
        if knesset_number is None:
            knesset = Knesset.objects.current_knesset()
        else:
            knesset = Knesset.objects.get(pk=knesset_number)

        mks_ids = Member.objects.filter(
            current_party__knesset=knesset).values_list('pk', flat=True)

        return [x for x in Agenda.objects.get_mks_values().get(self.id, []) if x[0] in mks_ids]

    def get_party_values(self):
        party_grades = Agenda.objects.get_all_party_values()
        return party_grades.get(self.id, [])

    def _get_suggested_generic(self, num, func):
        return func(Vote.objects.filter(~Q(agendavotes__agenda=self))).order_by('-score')[:num]
        
    def get_suggested_votes_by_agendas(self, num):
        def func(votes):
            return votes.annotate(score=Sum('agendavotes__importance'))
        return self._get_suggested_generic(num, func)

    def get_suggested_votes_by_controversy(self, num):
        def func(votes):
            return votes.extra(select={'score':'controversy'})
        return self._get_suggested_generic(num, func)

    def get_suggested_votes_by_agenda_tags(self, num):
        # TODO: This is untested, agendas currently don't have tags
        def func(votes):
            tag_importance_subquery = """
            SELECT sum(av.importance)
            FROM agendas_agendavote av
            JOIN tagging_taggeditem avti ON avti.object_id=av.id and avti.object_type_id=%s
            JOIN tagging_taggeditem ati ON ati.object_id=agendas_agenda.id and ati.object_type_id=%s
            WHERE avti.tag_id = ati.tag_id
            """
            agenda_type_id = ContentType.objects.get_for_model(self).id
            return votes.extra(select=dict(score=tag_importance_subquery),
                                select_params=[agenda_type_id] * 2)
        return self._get_suggested_generic(num, func)

SUMMARY_TYPES = (
    ('AG', 'Agenda Votes'),
    ('MK', 'MK Counter')
)

class SummaryAgenda(models.Model):
    agenda = models.ForeignKey(Agenda, related_name='score_summaries')
    month = models.DateTimeField(db_index=True)
    summary_type = models.CharField(max_length=2, choices=SUMMARY_TYPES)
    score = models.FloatField(default=0.0)
    votes = models.BigIntegerField(default=0)
    mk = models.ForeignKey(Member, blank=True, null=True, related_name='agenda_summaries')
    db_created = models.DateTimeField(auto_now_add=True)
    db_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'{} {} {} {} ({},{})'.format(self.agenda, self.month, self.summary_type,
                                            self.mk or 'n/a', self.score, self.votes)


def dateMonthTruncate(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def indexby(data, fieldFunc):
    d = defaultdict(list)
    for x in data:
        d[fieldFunc(x)].append(x)
    return d
