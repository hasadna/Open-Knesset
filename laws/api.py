'''
API for the laws app
'''
import logging
from django.core.urlresolvers import reverse
from tastypie.constants import ALL
import tastypie.fields as fields

from agendas.templatetags.agendas_tags import agendas_for

from apis.resources.base import BaseResource
from mks.models import Member, Party
from mks.api import MemberResource
from video.utils import get_videos_queryset
from video.api import VideoResource
from links.models import Link
from links.api import LinkResource
from models import Law, Bill, Vote, VoteAction, PrivateProposal

from simple.management.commands.syncdata_globals import p_explanation
from agendas.models import AgendaVote

from datetime import datetime, timedelta

logger = logging.getLogger("open-knesset.laws.api")


class LawResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = Law.objects.all()
        allowed_methods = ['get']


class VoteActionResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = VoteAction.objects.all()
        allowed_methods = ['get']
        excludes = ['type', 'id']
        include_resource_uri = False
        filtering = {
            'against_own_bill': ALL,
        }
        list_fields = [
            'member', 'party', 'vote', 'against_party', 'against_coalition', 'against_opposition', 'against_own_bill',
            'member_title', 'vote_title', 'member_url', 'vote_url', 'vote_time'
        ]

    vote_type = fields.CharField('type', null=True)
    member = fields.ToOneField(MemberResource, 'member', full=False)
    party = fields.ToOneField('mks.api.PartyResource', 'party', full=False)
    vote = fields.ToOneField('laws.api.VoteResource', 'vote', full=False)
    member_title = fields.CharField('member')
    vote_title = fields.CharField('vote')
    member_url = fields.CharField('member__get_absolute_url')
    vote_url = fields.CharField('vote__get_absolute_url')
    vote_time = fields.DateTimeField('vote__time')


class VoteResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = Vote.objects.all()
        allowed_methods = ['get']
        list_fields = [
            'time', 'title', 'vote_type', 'votes_count', 'for_votes_count',
            'against_votes_count', 'meeting_number', 'vote_number',
            'importance', 'controversy', 'against_party ', 'against_coalition',
            'against_opposition', 'against_own_bill',
        ]
        filtering = dict(tag=('exact'),
                         member=ALL,
                         member_for=ALL,
                         member_against=ALL,
                         from_date=ALL,
                         to_date=ALL)

    votes = fields.ToManyField(VoteActionResource,
                               attribute=lambda bundle: VoteAction.objects.filter(
                                       vote=bundle.obj).select_related('member'),
                               null=True,
                               full=True)
    agendas = fields.ListField()
    tags = fields.ToManyField('auxiliary.api.TagResource',
                              attribute=lambda t: t.obj.tags,
                              null=True,
                              full=False)

    def build_filters(self, filters={}):
        orm_filters = super(VoteResource, self).build_filters(filters)
        if 'member' in filters:
            orm_filters["voteaction__member"] = filters['member']
        if 'member_for' in filters:
            orm_filters["voteaction__member"] = filters['member_for']
            orm_filters["voteaction__type"] = 'for'
        if 'member_against' in filters:
            orm_filters["voteaction__member"] = filters['member_against']
            orm_filters["voteaction__type"] = 'against'
        if 'tag' in filters:
            # hard-coded the __in filter. not great, but works.
            orm_filters["tagged_items__tag__in"] = \
                filters["tag"].split(',')
        if 'from_date' in filters and filters.get('from_date'):
            orm_filters["time__gte"] = filters['from_date']
        if 'to_date' in filters:
            # the to_date needs to be incremented by a day since when humans say to_date=2014-07-30 they
            # actually mean midnight between 30 to 31. python on the other hand interperts this as midnight between
            # 29 and 30
            to_date = datetime.strptime(filters["to_date"], "%Y-%M-%d") + timedelta(days=1)
            orm_filters["time__lte"] = to_date.strftime("%Y-%M-%d")
        return orm_filters

    def dehydrate_agendas(self, bundle):
        agendavotes = bundle.obj.agendavotes.select_related('agenda')

        result = []
        for avote in agendavotes:
            agenda = avote.agenda
            resource_uri = reverse(
                    'api_dispatch_detail',
                    kwargs={
                        'resource_name': 'agenda', 'api_name': 'v2',
                        'pk': agenda.pk})

            agenda_bundle = {
                'name': agenda.name,
                'image': agenda.image.url if agenda.image else None,
                'resource_uri': resource_uri,
                'score': avote.score,
                'importance': avote.importance,
                'reasoning': avote.reasoning,
            }

            result.append(agenda_bundle)

        return result


class PrivateProposalResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = PrivateProposal.objects.all()
        allowed_methods = ['get']


class BillAgendaResource(BaseResource): pass


def detailed_agendas(agenda_list):
    result = []
    for xagenda in agenda_list:
        agenda = xagenda.agenda
        resource_uri = reverse(
                'api_dispatch_detail',
                kwargs={
                    'resource_name': 'agenda', 'api_name': 'v2',
                    'pk': agenda.pk})
        result.append({
            'name': agenda.name,
            'image': agenda.image.url if agenda.image else None,
            'resource_uri': resource_uri,
            'public_owner_name': agenda.public_owner_name,
            'reasoning': xagenda.reasoning,
            'score': xagenda.score,
            'importance': xagenda.importance,
        })

    return result


class BillResource(BaseResource):
    ''' Bill API '''

    class Meta(BaseResource.Meta):
        queryset = Bill.objects.all()
        allowed_methods = ['get']
        ordering = ['stage_date', 'title']
        filtering = dict(stage=ALL, proposer=ALL, title=ALL, full_title=ALL)
        list_fields = [
            'title', 'full_title', 'popular_name', 'law', 'stage',
            'stage_date'
        ]
        include_absolute_url = True
        limit = 20

    explanation = fields.CharField()
    legal_code = fields.CharField()
    proposers = fields.ToManyField(MemberResource,
                                   'proposers',
                                   full=False)
    pre_votes = fields.ToManyField(VoteResource,
                                   'pre_votes',
                                   null=True,
                                   full=False)

    first_vote = fields.ToOneField(VoteResource,
                                   'first_vote',
                                   null=True,
                                   full=False)

    approval_vote = fields.ToOneField(VoteResource,
                                      'approval_vote',
                                      null=True,
                                      full=False)
    proposals = fields.ToManyField(PrivateProposalResource,
                                   'proposals',
                                   null=True,
                                   full=True)
    tags = fields.ToManyField('auxiliary.api.TagResource',
                              attribute=lambda t: t.obj.tags,
                              null=True,
                              full=False)

    # XXX : this adds the following select phrases
    # [sql] SELECT ...
    # FROM "agendas_agendabill"
    # WHERE ("agendas_agendabill"."agenda_id" IN
    # (SELECT ...
    # FROM "agendas_agenda"
    # WHERE "agendas_agenda"."is_public" = TRUE)
    # AND "agendas_agendabill"."bill_id" = XXX)
    # [sql] SELECT ...
    # FROM "agendas_agenda"
    # WHERE "agendas_agenda"."id" = YYY
    agendas = fields.ToManyField(BillAgendaResource,
                                 'agendas',

                                 null=True,
                                 full=False)

    def dehydrate_agendas(self, bundle):
        result = None
        try:
            result = dict()
            # fast-written and ugly code
            agendas_detailes = agendas_for(bundle.request.user, bundle.obj, 'bill')

            result["agenda_list"] = detailed_agendas(agendas_detailes["agendas"])
            result["suggest_agendas"] = agendas_detailes[
                "suggest_agendas"]  # XXX : should i call detailed_agendas here too?

            # XXX : there was no data examples here and i dont understand the data-structure that good. there should probably be a special handling for forms
            result["formset"] = agendas_detailes["formset"]
            result["suggested_agendas"] = agendas_detailes[
                "suggested_agendas"]  # XXX : should i call detailed_agendas here three?
            result["suggest_agendas_login"] = agendas_detailes["suggest_agendas_login"]

            return result

        except:
            logging.error('Got exception dehydrating agendas')

        return None

    def dehydrate_explanation(self, bundle):
        result = None
        try:
            result = self.get_src_parts(bundle)[1]
        except:
            logging.error('Got exception dehydrating explanation')
            return ""
            # TODO: do we need this here????
            # return result

    def dehydrate_legal_code(self, bundle):
        return self.get_src_parts(bundle)[0]

    def dehydrate_stage(self, bundle):
        return bundle.obj.get_stage_display()

    def get_src_parts(self, bundle):
        try:
            return bundle.src_parts
        except AttributeError:
            parts = ['', '']
            bill = bundle.obj
            try:
                ps = bill.proposals.order_by('-date')[0]
                if ps.content_html:
                    parts = ps.content_html.split(p_explanation)
            except IndexError:
                pass
            bundle.src_parts = parts
        return parts

    def build_filters(self, filters={}):
        orm_filters = super(BillResource, self).build_filters(filters)
        if 'proposer' in filters:
            orm_filters["proposers"] = filters['proposer']
        return orm_filters
