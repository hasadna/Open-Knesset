'''
Api for the committees app
'''
from tastypie.api import Api
from tastypie.constants import ALL
from tastypie.bundle import Bundle
import tastypie.fields as fields

from apis.resources.base import BaseResource
from models import Committee, CommitteeMeeting, ProtocolPart
from mks.api import MemberResource


class CommitteeResource(BaseResource):
    ''' Committee API
    '''
    recent_meetings = fields.ListField()
    future_meetings = fields.ListField()

    class Meta:
        queryset = Committee.objects.all()
        allowed_methods = ['get']
        include_absolute_url = True

    def dehydrate_recent_meetings(self, bundle):
        return [ { 'url': x.get_absolute_url(),
                   'title': x.title(),
                   'date': x.date }
                for x in bundle.obj.recent_meetings() ]

    def dehydrate_future_meetings(self, bundle):
        return [ { 'title': x.what,
                   'date': x.when }
                for x in bundle.obj.future_meetings() ]


class CommitteeMeetingResource(BaseResource):
    ''' Committee Meeting API
    '''
    committee = fields.ForeignKey(CommitteeResource, 'committee')
    mks_attended = fields.ToManyField(MemberResource, 'mks_attended')
    protocol = fields.ToManyField('committees.api.ProtocolPartResource',
                                  'parts', full=True)
    class Meta:
        queryset = CommitteeMeeting.objects.all().select_related('committee',
                                                                 'mks_attended',
                                                                 ).prefetch_related('parts')
        allowed_methods = ['get']
        include_absolute_url = True
        list_fields = ['committee','mks_attended','date','topics']
        excludes = ['protocol_text']

class ProtocolPartResource(BaseResource):
    header = fields.CharField(attribute='header')
    body = fields.CharField(attribute='body')
    class Meta:
        queryset = ProtocolPart.objects.all().order_by('order')
        allowed_methods = ['get']
        fields = list_fields = ['header','body']
        include_resource_uri = False
