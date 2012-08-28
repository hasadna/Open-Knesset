from django.conf import settings
from django.conf.urls.defaults import *
from mmm.models import Document


urlpatterns = patterns('',
    url(r'^member/(?P<mid>\d+)/$', 
        'knesset.mmm.views.member_docs',
        name='member-mmms'),
    url(r'^committee/(?P<cid>\d+)/$', 
        'knesset.mmm.views.committee_docs', 
        name='committee-mmms'),
)