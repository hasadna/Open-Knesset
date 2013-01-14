'''
Api for the members app
'''
import urllib
from django.core.urlresolvers import reverse
from django.core.cache import cache
from tastypie.constants import ALL
from tastypie.bundle import Bundle
import tastypie.fields as fields

from apis.resources.base import BaseResource
from models import CandidateList

class CandidateListResource(BaseResource):
    ''' Candidat List API
    TBD: create a party app
    '''

    class Meta:
        queryset = CandidateList.objects.all()
        allowed_methods = ['get']
        excludes = ['end_date', 'start_date']
        list_fields = ["id", "name", "ballot", ]

