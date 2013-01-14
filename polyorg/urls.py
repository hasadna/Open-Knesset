from django.conf.urls.defaults import *
from views import *

polyorgurlpatterns = patterns('polyorg.views',
        url(r'list/$', CandidateListListView.as_view(), name='candidate-list-list'),
        url(r'list/(?P<pk>\d+)/$', CandidateListDetailView.as_view(), name='candidate-list-detail'),
    )

