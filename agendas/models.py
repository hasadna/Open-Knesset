from itertools import chain
from django.db import models
from django.db.models import Sum, Q, Count
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.conf import settings

from django.contrib.auth.models import User
from actstream.models import Follow
from laws.models import VoteAction, Vote
from mks.models import Party, Member
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

class AgendaVote(models.Model):
    agenda = models.ForeignKey('Agenda', related_name='agendavotes')
    vote = models.ForeignKey('laws.Vote', related_name='agendavotes')
    score = models.FloatField(default=0.0, choices=AGENDAVOTE_SCORE_CHOICES)
    importance = models.FloatField(default=1.0, choices=IMPORTANCE_CHOICES)
    reasoning = models.TextField(null=True,blank=True)

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
        return None

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
        bottom = bottom - delta/2
        if delta%2:
            top = top - delta/2 -1
        else:
            top = top - delta/2
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

    def get_all_party_values(self):
        allAgendaPartyVotes = cache.get('AllAgendaPartyVotes')
        if not allAgendaPartyVotes:
            allAgendaPartyVotes = queries.getAllAgendaPartyVotes()
            cache.set('AllAgendaPartyVotes',allAgendaPartyVotes,1800)
        return allAgendaPartyVotes

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

    def get_mks_values(self):
        mks_grade = Agenda.objects.get_mks_values()
        return mks_grade.get(self.id,[])

    def get_mks_totals(self, member):
        "Get count for each vote type for a specific member on this agenda"

        # let's split qs to make it more readable
        qs = VoteAction.objects.filter(member=member, vote__agendavotes__agenda=self)
        qs = qs.values('type').annotate(total=Count('id'))
        return qs

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

from listeners import *
from operator import itemgetter, attrgetter
