'''
Api for the members app
'''
import urllib
from django.core.urlresolvers import reverse
from tastypie.constants import ALL
from tastypie.bundle import Bundle
import tastypie.fields as fields

from knesset.api.resources.base import BaseResource
from knesset.committees.models import Committee, CommitteeMeeting

class CommitteeResource(BaseResource):
    ''' Committee API
    '''

    class Meta:
        queryset = Committee.objects.all()
        allowed_methods = ['get']
        #excludes = ['end_date', 'start_date']
        include_absolute_url = True
