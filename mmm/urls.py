from django.conf import settings
from django.conf.urls.defaults import url, patterns
from models import Document

urlpatterns = patterns('mmm.views',
    url(r'^member/(?P<mid>\d+)/$',
        'member_docs',
        name='member-mmms'),
    url(r'^committee/(?P<cid>\d+)/$',
        'committee_docs',
        name='committee-mmms'),
)
