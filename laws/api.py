'''
API for the laws app
'''
import logging

from django.core.urlresolvers import reverse
from tastypie.constants import ALL
import tastypie.fields as fields

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

logger = logging.getLogger("open-knesset.laws.api")

class LawResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = Law.objects.all()
        allowed_methods = ['get']

class VoteActionResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = VoteAction.objects.all()
        allowed_methods = ['get']
        excludes = ['type','id']
        include_resource_uri = False

    vote_type = fields.CharField('type',null=True)
    member = fields.ToOneField(MemberResource,
                              'member',
                              full=False)


class VoteResource(BaseResource):

    class Meta(BaseResource.Meta):
        queryset = Vote.objects.all()
        allowed_methods = ['get']
        list_fields = [
            'time', 'title', 'votes_count', 'for_votes_count',
            'against_votes_count', 'meeting_number', 'vote_number',
            'importance', 'controversy', 'against_party ', 'against_coalition',
            'against_opposition', 'against_own_bill',
        ]
        filtering = dict(member=ALL,
                         member_for=ALL,
                         member_against=ALL)

    votes = fields.ToManyField(VoteActionResource,
                    attribute=lambda bundle:VoteAction.objects.filter(
                                    vote=bundle.obj).select_related('member'),
                    null=True,
                    full=True)
    agendas = fields.ListField()

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


class BillResource(BaseResource):
    ''' Bill API '''

    class Meta(BaseResource.Meta):
        queryset = Bill.objects.all()
        allowed_methods = ['get']
        ordering = ['stage_date', 'title']
        filtering = dict(stage=ALL, proposer=ALL)
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


    def dehydrate_explanation(self, bundle):
        result = None
        try:
            result = self.get_src_parts(bundle)[1]
        except:
            logging.error('Got exception dehydrating explanation')
            return ""

    def dehydrate_legal_code(self, bundle):
        return self.get_src_parts(bundle)[0]

    def dehydrate_stage(self, bundle):
        return bundle.obj.get_stage_display()

    def get_src_parts(self, bundle):
        try:
            return bundle.src_parts
        except AttributeError:
            parts = ['','']
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
