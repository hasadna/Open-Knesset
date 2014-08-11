from __future__ import division
from itertools import chain
from operator import itemgetter, attrgetter
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
from actstream.models import Follow
from laws.models import VoteAction, Vote
from mks.models import Party, Member, Knesset
import queries

AGENDAVOTE_SCORE_CHOICES = (
    ('',_("Not selected")),
    (-1.0, _("Opposes fully")),
    (-0.5, _("Opposes partially")),
    (0.0, _("Agnostic")),
    (0.5, _("Complies partially")),
    (1.0, _("Complies fully")),
)
IMPORTANCE_CHOICES = (
    ('',_("Not selected")),
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
        unique_together = ('agenda','vote','user')

class AgendaVoteManager(models.Manager):
    db_month_trunc_functions = {
        'sqlite3':{'monthfunc':"strftime('%%Y-%%m-01'",'nowfunc':'date()'},
        'postgresql_psycopg2':{'monthfunc':"date_trunc('month'",'nowfunc':'now()'}
    }

    def compute_all(self):
        db_engine = settings.DATABASES['default']['ENGINE']
        db_functions = self.db_month_trunc_functions[db_engine.split('.')[-1]]
        agenda_query = queries.BASE_AGENDA_QUERY % db_functions
        cursor = connection.cursor()
        cursor.execute(agenda_query)

        mk_query = queries.BASE_MK_QUERY % db_functions
        cursor.execute(mk_query)


class AgendaVote(models.Model):
    agenda = models.ForeignKey('Agenda', related_name='agendavotes')
    vote = models.ForeignKey('laws.Vote', related_name='agendavotes')
    score = models.FloatField(default=0.0, choices=AGENDAVOTE_SCORE_CHOICES)
    importance = models.FloatField(default=1.0, choices=IMPORTANCE_CHOICES)
    reasoning = models.TextField(null=True,blank=True)

    objects = AgendaVoteManager()

    def detail_view_url(self):
        return reverse('agenda-vote-detail', args=[self.pk])

    def get_score_header(self):
        return _('Position')
    def get_importance_header(self):
        return _('Importance')

    class Meta:
        unique_together= ('agenda', 'vote')

    def __unicode__(self):
        return u"%s %s" % (self.agenda,self.vote)

    def update_monthly_counters(self):
        agendaScore     = float(self.score) * float(self.importance)
        objMonth        = dateMonthTruncate(self.vote.time)

        summaryObjects  = list(SummaryAgenda.objects.filter( agenda=self.agenda,
                                                            month=objMonth).all())

        agendaSummary   = None
        if not filter(lambda summary:summary.summary_type=='AG',summaryObjects):
            agendaSummary   = SummaryAgenda(month=objMonth,
                                            agenda=self.agenda,
                                            summary_type='AG',
                                            score=abs(agendaScore),
                                            votes=1)
        else:
            existingAgenda = filter(lambda summary:summary.summary_type=='AG',summaryObjects)[0]
            existingAgenda.votes += 1
            existingAgenda.score += abs(agendaScore)
            existingAgenda.save()

        agendasByMk     = dict(map(lambda summary:(summary.mk_id,summary),
                                   filter(lambda summary:summary.summary_type=='MK',
                                          summaryObjects)))
        newObjects = []
        if agendaSummary:
            newObjects.append(agendaSummary)
        voters = defaultdict(list)
        for vote_action in self.vote.voteaction_set.all():
            mkSummary = agendasByMk.get(vote_action.member_id, None)
            if not mkSummary:
                mkSummary = SummaryAgenda(month=objMonth,
                                          agenda=self.agenda,
                                          summary_type='MK',
                                          mk_id=vote_action.member_id,
                                          votes=1,
                                          score=agendaScore * (1 if vote_action.type == 'for' else -1),
                                          for_votes=(1 if vote_action.type == 'for' else 0),
                                          against_votes=(1 if vote_action.type == 'against' else 0))
                newObjects.append(mkSummary)
            else:
                voters[vote_action.type].append(vote_action.member_id)

        SummaryAgenda.objects.filter(agenda=self.agenda,mk_id__in=voters['for'],month=objMonth).update(votes=F('votes') + 1, score=F('score')+agendaScore, for_votes=F('for_votes') + 1)
        SummaryAgenda.objects.filter(agenda=self.agenda,mk_id__in=voters['against'],month=objMonth).update(votes=F('votes') + 1, score=F('score')-agendaScore, against_votes=F('against_votes') + 1)
        if newObjects:
            SummaryAgenda.objects.bulk_create(newObjects)

    def save(self,*args,**kwargs):
        super(AgendaVote,self).save(*args,**kwargs)
        self.update_monthly_counters()

class AgendaMeeting(models.Model):
    agenda = models.ForeignKey('Agenda', related_name='agendameetings')
    meeting = models.ForeignKey('committees.CommitteeMeeting',
                                related_name='agendacommitteemeetings')
    score = models.FloatField(default=0.0, choices=IMPORTANCE_CHOICES)
    reasoning = models.TextField(null=True)

    def detail_view_url(self):
        return reverse('agenda-meeting-detail', args=[self.pk])

    def get_score_header(self):
        return _('Importance')
    def get_importance_header(self):
        return ''

    class Meta:
        unique_together = ('agenda', 'meeting')

    def __unicode__(self):
        return u"%s %s" % (self.agenda,self.meeting)

class AgendaBill(models.Model):
    agenda = models.ForeignKey('Agenda', related_name='agendabills')
    bill = models.ForeignKey('laws.bill', related_name='agendabills')
    score = models.FloatField(default=0.0, choices=AGENDAVOTE_SCORE_CHOICES)
    importance = models.FloatField(default=1.0, choices=IMPORTANCE_CHOICES)
    reasoning = models.TextField(null=True)

    def detail_view_url(self):
        return reverse('agenda-bill-detail', args=[self.pk])

    def get_score_header(self):
        return _('Position')
    def get_importance_header(self):
        return _('Importance')

    class Meta:
        unique_together = ('agenda', 'bill')

    def __unicode__(self):
        return u"%s %s" % (self.agenda,self.bill)

def get_top_bottom(lst, top, bottom):
    """
    Returns a cropped list, keeping some of the list's top and bottom.
    Edge conditions are handled gracefuly.
    Input list should be ascending so that top is at the end.
    """
    if len(lst) < top+bottom:
        delta = top+bottom - len(lst)
        bottom = bottom - int(math.floor(delta/2))
        if delta%2:
            top = top - int(math.floor(delta/2)) -1
        else:
            top = top - int(math.floor(delta/2))
    if top and bottom:
        top_lst = lst[-top:]
        bottom_lst = lst[:bottom]
    elif top:
        top_lst = lst[-top:]
        bottom_lst = []
    elif bottom:
        top_lst = []
        bottom_lst = lst[:bottom]
    else:
        top_lst = []
        bottom_lst = []

    return {'top':top_lst,
            'bottom':bottom_lst}


class AgendaManager(models.Manager):

    def get_selected_for_instance(self, instance, user=None, top=3, bottom=3):
        # Returns interesting agendas for model instances such as: member, party
        agendas = list(self.get_relevant_for_user(user))
        for agenda in agendas:
            agenda.score = agenda.__getattribute__('%s_score' % instance.__class__.__name__.lower())(instance)
            agenda.significance = agenda.score * agenda.num_followers
        agendas.sort(key=attrgetter('significance'))
        agendas = get_top_bottom(agendas, top, bottom)
        agendas['top'].sort(key=attrgetter('score'), reverse=True)
        agendas['bottom'].sort(key=attrgetter('score'), reverse=True)
        return agendas

    def get_relevant_for_mk(self, mk, agendaId):
        agendas = AgendaVote.objects.filter(agenda__id=agendaId,vote__votes__id=mk).distinct()
        return agendas

    def get_relevant_for_user(self, user):
        if user == None or not user.is_authenticated():
            agendas = Agenda.objects.filter(is_public=True)\
                                    .order_by('-num_followers')\
                                    .prefetch_related('agendavotes')
        elif user.is_superuser:
            agendas = Agenda.objects.all().order_by('-num_followers')\
                                          .prefetch_related('agendavotes')
        else:
            agendas = Agenda.objects.filter(Q(is_public=True) |
                                            Q(editors=user))\
                                    .order_by('-num_followers')\
                                    .prefetch_related('agendavotes')\
                                    .distinct()
        return agendas

    def get_possible_to_suggest(self, user, vote):
        if user == None or not user.is_authenticated():
            agendas = False
        else:
            agendas = Agenda.objects.filter(is_public=True)\
                            .exclude(editors=user)\
                            .exclude(agendavotes__vote=vote)\
                            .distinct()
        return agendas

    def get_mks_values(self):
        mks_values = cache.get('agendas_mks_values')
        if not mks_values:
            q = queries.agendas_mks_grade()
            # outer join - add missing mks to agendas
            newAgendaMkVotes = {}
            # generates a set of all the current mk ids that have ever voted for any agenda
            # its not perfect, but its better than creating another query to generate all known mkids
            allMkIds = set(map(itemgetter(0),chain.from_iterable(q.values())))
            for agendaId,agendaVotes in q.items():
                # the newdict will have 0's for each mkid, the update will change the value for known mks
                newDict = {}.fromkeys(allMkIds,(0,0,0))
                newDict.update(dict(map(lambda (mkid,score,volume,numvotes):(mkid,(score,volume,numvotes)),agendaVotes)))
                newAgendaMkVotes[agendaId]=newDict.items()
            mks_values = {}
            for agenda_id, scores in newAgendaMkVotes.items():
                mks_values[agenda_id] = \
                    map(lambda x: (x[1][0], dict(score=x[1][1][0], rank=x[0], volume=x[1][1][1], numvotes=x[1][1][2])),
                        enumerate(sorted(scores,key=lambda x:x[1][0],reverse=True), 1))
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

class Agenda(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(null=True,blank=True)
    editors = models.ManyToManyField('auth.User', related_name='agendas')
    votes = models.ManyToManyField('laws.Vote',through=AgendaVote)
    public_owner_name = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)
    num_followers = models.IntegerField(default=0)
    image = models.ImageField(blank=True, null=True, upload_to='agendas')

    objects = AgendaManager()

    class Meta:
        verbose_name = _('Agenda')
        verbose_name_plural = _('Agendas')
        unique_together = (("name", "public_owner_name"),)

    def __unicode__(self):
        return u"%s %s %s" % (self.name,_('edited by'),self.public_owner_name)

    @models.permalink
    def get_absolute_url(self):
        return ('agenda-detail', [str(self.id)])

    @models.permalink
    def get_edit_absolute_url(self):
        return ('agenda-detail-edit', [str(self.id)])

    def member_score(self, member):
        # Find all votes that
        #   1) This agenda is ascribed to
        #   2) the member participated in and either voted for or against
        qs = AgendaVote.objects.filter(
            agenda = self,
            vote__voteaction__member = member,
            vote__voteaction__type__in=['for','against']).extra(
                select={'weighted_score':'agendas_agendavote.score*agendas_agendavote.importance'}
            ).values_list('weighted_score','vote__voteaction__type')

        for_score = against_score = 0
        for score, action_type in qs:
            if action_type == 'against':
                against_score += score
            else:
                for_score += score

        max_score = sum([abs(x.score*x.importance) for x in
                         self.agendavotes.all()])
        if max_score > 0:
            return (for_score - against_score) / max_score * 100
        else:
            return 0.0

    def party_score(self, party):
        # Since we're already calculating python side, no need to do 2 queries
        # with joins, select for and against, and calcualte the things
        qs = AgendaVote.objects.filter(
            agenda=self, vote__voteaction__member__in=party.members.all(),
            vote__voteaction__type__in=['against', 'for']).extra(
                select={'weighted_score': 'agendas_agendavote.score*agendas_agendavote.importance'}
            ).values_list('weighted_score', 'vote__voteaction__type')

        for_score = 0
        against_score = 0

        for score, action_type in qs:
            if action_type == 'against':
                against_score += score
            else:
                for_score += score

        #max_score = sum([abs(x) for x in self.agendavotes.values_list('score', flat=True)]) * party.members.count()
        # To save the queries, make sure to pass prefetch/select related
        # Removed the values call, so that we can utilize the prefetched stuf
        # This reduces the number of queries when called for example from
        # AgendaResource.dehydrate
        max_score = sum(abs(x.score * x.importance) for x in
                        self.agendavotes.all()) * party.number_of_seats

        if max_score > 0:
            return (for_score - against_score) / max_score * 100
        else:
            return 0.0

    def candidate_list_score(self, candidate_list):
        # Since we're already calculating python side, no need to do 2 queries
        # with joins, select for and against, and calcualte the things
        qs = AgendaVote.objects.filter(
            agenda=self, vote__voteaction__member__in=candidate_list.member_ids,
            vote__voteaction__type__in=['against', 'for']).extra(
                select={'weighted_score': 'agendas_agendavote.score*agendas_agendavote.importance'}
            ).values_list('weighted_score', 'vote__voteaction__type')

        for_score = 0
        against_score = 0

        for score, action_type in qs:
            if action_type == 'against':
                against_score += score
            else:
                for_score += score

        #max_score = sum([abs(x) for x in self.agendavotes.values_list('score', flat=True)]) * party.members.count()
        # To save the queries, make sure to pass prefetch/select related
        # Removed the values call, so that we can utilize the prefetched stuf
        # This reduces the number of queries when called for example from
        # AgendaResource.dehydrate
        max_score = sum(abs(x.score * x.importance) for x in
                        self.agendavotes.all()) * len(candidate_list.member_ids)

        if max_score > 0:
            return (for_score - against_score) / max_score * 100
        else:
            return 0.0

    def related_mk_votes(self,member):
        # Find all votes that
        #   1) This agenda is ascribed to
        #   2) the member participated in and either voted for or against
        # for_votes      = AgendaVote.objects.filter(agenda=self,vote__voteaction__member=member,vote__voteaction__type="for").distinct()
        #against_votes   = AgendaVote.objects.filter(agenda=self,vote__voteaction__member=member,vote__voteaction__type="against").distinct()
        vote_actions = VoteAction.objects.filter(member=member,vote__agendavotes__agenda=self)
        all_votes = AgendaVote.objects.filter(agenda=self,vote__voteaction__member=member).distinct()
        # TODO: improve ugly code below
        member_votes = list()
        for member_vote in all_votes:
            for vote_action in vote_actions:
                if (vote_action.vote == member_vote.vote):
                    member_votes.insert(0,member_vote)
                    member_votes[0].voteaction = vote_action

        return member_votes
        #return AgendaVote.objects.filter(agenda=self,vote__voteaction__member=mk).distinct()

    def selected_instances(self, cls, top=3, bottom=3):
        instances = list(cls.objects.all())
        for instance in instances:
            instance.score = self.__getattribute__('%s_score' % instance.__class__.__name__.lower())(instance)
        instances.sort(key=attrgetter('score'))
        instances = get_top_bottom(instances, top, bottom)
        instances['top'].sort(key=attrgetter('score'), reverse=True)
        instances['bottom'].sort(key=attrgetter('score'), reverse=True)
        return instances

    def generateSummaryFilters(self,ranges):
        results = []
        for r in ranges:
            if not r[0] and not r[1]:
                return None # might as well not filter at all
            queryFields = {}
            if r[0]:
                queryFields['month__gte']=r[0]
            if r[1]:
                queryFields['month__lt']=r[1]
            results.append(Q(**queryFields))
        return results

    def get_mks_totals(self, member):
        "Get count for each vote type for a specific member on this agenda"

        # let's split qs to make it more readable
        qs = VoteAction.objects.filter(member=member, type__in=('for', 'against'), vote__agendavotes__agenda=self)
        qs = list(qs.values('type').annotate(total=Count('id')))

        totals = sum(x['total'] for x in qs)
        qs.append({'type': 'no-vote', 'total': self.votes.count() - totals})

        return qs

    def get_mks_values(self,ranges=None):
        if ranges is None:
            ranges = [[dateMonthTruncate(Knesset.objects.current_knesset().start_date),None]]
        mks_values = False
        fullRange = ranges == [[None,None]]
        if fullRange:
            mks_values = cache.get('agenda_%d_mks_values' % self.id)

	if not mks_values:
	    # fix the mks part from https://github.com/hasadna/Open-Knesset/issues/228
	    if ranges[0][1] is None:
		# if there are no end in the range object check only if the start date greater
		# or equal to the start of the range 
		mk_ids = Member.objects.filter(current_party__isnull=False,start_date__gte = ranges[0][0]).values_list('id',flat=True)
	    else:
		# else check also that the start date is less then the end date 
		mk_ids = Member.objects.filter(current_party__isnull=False,start_date__gte = ranges[0][0],start_date__lte = ranges[0][1]).values_list('id',flat=True)
        

            # generate summary query
            filterList = self.generateSummaryFilters(ranges)

            # query summary
            baseQuerySet = SummaryAgenda.objects.filter(agenda=self)
            if filterList:
                if len(filterList)>1:
                    filtersFolded = reduce(lambda x,y:x | y, filterList)
                else:
                    filtersFolded = filterList[0]
                baseQuerySet.filter(filtersFolded)
            summaries = list(baseQuerySet)
            # group summaries for respective ranges
            summariesForRanges = []
            for r in ranges:
                summariesForRange = defaultdict(list)
                for s in summaries:
                    if (not r[0] or s.month>=r[0]) and \
                        (not r[1] or s.month<r[1]):
                        summariesForRange[s.summary_type].append(s)
                summariesForRanges.append(summariesForRange)

            # compute agenda measures, store results per MK
            mk_results = dict(map(lambda mk_id:(mk_id,[]),mk_ids))
            for summaries in summariesForRanges:
                agenda_data             = summaries['AG']
                total_votes             = sum(map(attrgetter('votes'),agenda_data))
                total_for_votes         = sum(map(attrgetter('for_votes'),agenda_data))
                total_against_votes     = sum(map(attrgetter('against_votes'),agenda_data))                
                total_score             = sum(map(attrgetter('score'),agenda_data))
                current_mks_data        = indexby(summaries['MK'],attrgetter('mk_id'))
                # calculate results per mk
                rangeMkResults          = []
                for mk_id in mk_results.keys():
                    mk_data     = current_mks_data[mk_id]
                    if mk_data:
                        mk_votes            = sum(map(attrgetter('votes'),mk_data))
                        mk_for_votes        = sum(map(attrgetter('for_votes'),mk_data))
                        mk_against_votes    = sum(map(attrgetter('against_votes'),mk_data))
                        mk_volume           = 100*mk_votes/total_votes
                        mk_score            = 100*sum(map(attrgetter('score'),mk_data))/total_score if total_score != 0 else 0
                        rangeMkResults.append((mk_id,mk_votes,mk_for_votes,mk_against_votes,mk_score,mk_volume))
                    else:
                        rangeMkResults.append(tuple([mk_id]+[0]*5))
                # sort results by score descending
                for rank,(mk_id,mk_votes,mk_for_votes,mk_against_votes,mk_score,mk_volume) in enumerate(sorted(rangeMkResults,key=itemgetter(4,0),reverse=True)):
                    mk_range_data = dict(score=mk_score,rank=rank,volume=mk_volume,numvotes=mk_votes,numforvotes=mk_for_votes,numagainstvotes=mk_against_votes)
                    if len(ranges)==1:
                        mk_results[mk_id]=mk_range_data
                    else:
                        mk_results[mk_id].append(mk_range_data)
            if fullRange:
                cache.set('agenda_%d_mks_values' % self.id, mks_values, 1800)
        if len(ranges)==1:
            mk_results = sorted(mk_results.items(),key=lambda (k,v):v['rank'])
        return mk_results


    def get_mks_values_old(self, knesset_number=None):
        """Return mks values.

        :param knesset_number: The knesset numer of the mks. ``None`` will
                               return current knesset (default: ``None``).
        """
        mks_grade = Agenda.objects.get_mks_values()

        if knesset_number is None:
            knesset = Knesset.objects.current_knesset()
        else:
            knesset = Knesset.objects.get(pk=knesset_number)

        mks_ids = Member.objects.filter(
            current_party__knesset=knesset).values_list('pk', flat=True)

        grades = mks_grade.get(self.id, [])
        current_grades = [x for x in grades if x[0] in mks_ids]
        return current_grades

    def get_party_values(self):
        party_grades = Agenda.objects.get_all_party_values()
        return party_grades.get(self.id,[])

    def get_all_party_values(self):
        return Agenda.objects.get_all_party_values()

    def get_suggested_votes_by_agendas(self, num):
        votes = Vote.objects.filter(~Q(agendavotes__agenda=self))
        votes = votes.annotate(score=Sum('agendavotes__importance'))
        return votes.order_by('-score')[:num]

    def get_suggested_votes_by_agenda_tags(self, num):
        # TODO: This is untested, agendas currently don't have tags
        votes = Vote.objects.filter(~Q(agendavotes__agenda=self))
        tag_importance_subquery = """
        SELECT sum(av.importance)
        FROM agendas_agendavote av
        JOIN tagging_taggeditem avti ON avti.object_id=av.id and avti.object_type_id=%s
        JOIN tagging_taggeditem ati ON ati.object_id=agendas_agenda.id and ati.object_type_id=%s
        WHERE avti.tag_id = ati.tag_id
        """
        agenda_type_id = ContentType.objects.get_for_model(self).id
        votes = votes.extra(select=dict(score = tag_importance_subquery),
                            select_params = [agenda_type_id]*2)
        return votes.order_by('-score')[:num]

    def get_suggested_votes_by_controversy(self, num):
        votes = Vote.objects.filter(~Q(agendavotes__agenda=self))
        votes = votes.extra(select=dict(score = 'controversy'))
        return votes.order_by('-score')[:num]

SUMMARY_TYPES = (
    ('AG','Agenda Votes'),
    ('MK','MK Counter')
)

class SummaryAgenda(models.Model):
    agenda          = models.ForeignKey(Agenda, related_name='score_summaries')
    month           = models.DateTimeField(db_index=True)
    summary_type    = models.CharField(max_length=2, choices=SUMMARY_TYPES)
    score           = models.FloatField(default=0.0)
    votes           = models.BigIntegerField(default=0)
    for_votes       = models.BigIntegerField(default=0)
    against_votes   = models.BigIntegerField(default=0)
    mk              = models.ForeignKey(Member,blank=True, null=True, related_name='agenda_summaries')
    db_created      = models.DateTimeField(auto_now_add=True)
    db_updated      = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "%s %s %s %s (%f,%d)" % (str(self.agenda_id),str(self.month),self.summary_type,str(self.mk_id) if self.mk else u'n/a',self.score,self.votes)

from listeners import *

def dateMonthTruncate(dt):
    dt = dt.replace(day=1)
    if type(dt) == datetime.datetime:
        dt = dt.replace(hour=0,minute=0,second=0,microsecond=0)
    else:
        dt = datetime.datetime(year=dt.year,month=dt.month,day=1)
    return dt

def indexby(data,fieldFunc):
    d = defaultdict(list)
    for k,v in map(lambda d:(fieldFunc(d),d),data):
        d[k].append(v)
    return d
