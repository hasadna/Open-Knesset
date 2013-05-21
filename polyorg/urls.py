from django.conf.urls.defaults import url, patterns
from views import CandidateListListView, CandidateListDetailView
from views import CandidateListCompareView

polyorgurlpatterns = patterns('polyorg.views',
        url(r'list/$', CandidateListListView.as_view(), name='candidate-list-list'),
        url(r'list/(?P<pk>\d+)/$', CandidateListDetailView.as_view(), name='candidate-list-detail'),
        url(r'compare/$', CandidateListCompareView.as_view(), name='candidate-list-compare'),
    )
