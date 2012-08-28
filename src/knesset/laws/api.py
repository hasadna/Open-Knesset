'''
API for the laws app
'''
from tastypie.constants import ALL
import tastypie.fields as fields

from knesset.api.resources.base import BaseResource
from mks.models import Member, Party
from mks.api import MemberResource
from video.utils import get_videos_queryset
from video.api import VideoResource
from links.models import Link
from links.api import LinkResource
from models import Law, Bill, Vote

class LawResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = Law.objects.all()
        allowed_methods = ['get']

class VoteResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = Vote.objects.all()
        allowed_methods = ['get']
        exclude_from_list_view = ['members',]
        filtering = dict(member = ALL,
                         member_for = ALL,
                         member_against = ALL)

    members = fields.ToManyField(MemberResource,
                    'votes',
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

        return orm_filters

class BillResource(BaseResource):
    ''' Bill API '''
    class Meta(BaseResource.Meta):
        queryset = Bill.objects.all()
        allowed_methods = ['get']
        # excludes = ['stage']
        ordering = ['stage_date', 'title']
        filtering = dict(stage = ALL, proposer = ALL)
        exclude_from_list_view = ['proposers', 'explanation', 'legal_code',
        'pre_votes', 'first_vote', 'approval_vote']
        include_absolute_url = True

    explanation = fields.CharField()
    legal_code = fields.CharField()
    proposers = fields.ToManyField(MemberResource,
                    'proposers',
                    full=True)
    pre_votes = fields.ToManyField(VoteResource,
                    'pre_votes',
                    null=True,
                    full=True)

    first_vote = fields.ToOneField(VoteResource,
                    'first_vote',
                    null=True,
                    full=True)

    approval_vote = fields.ToOneField(VoteResource,
                    'approval_vote',
                    null=True,
                    full=True)


    def dehydrate_explanation(self, bundle):
        return self.get_src_parts(bundle)[1]

    def dehydrate_legal_code(self, bundle):
        return self.get_src_parts(bundle)[0]

    def dehydrate_stage(self, bundle):
        return bundle.obj.get_stage_display()

    def get_src_parts(self, bundle):
        try:
            return bundle.src_parts
        except AttributeError:
            parts = ['','']
            from simple.management.commands.syncdata import p_explanation
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
