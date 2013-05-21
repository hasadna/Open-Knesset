from django.conf.urls.defaults import url, patterns
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404

from mock import mock_reader
from backlinks.pingback.server import PingbackServer
from backlinks.trackback.server import TrackBackServer
from backlinks.pingback.server import default_server
from mks.views import get_mk_entry, mk_is_backlinkable, mk_detail

# Mock server classes

class MockTrackBackServer(TrackBackServer):
    url_reader = mock_reader

# Mock target getter and validator

# Mock target view


#entry_detail = mock_pingback_server.register_view(mk_detail, get_entry_from_object_id, entry_is_pingable)
default_server.url_reader = mock_reader

#entry_detail = mock_pingback_server.register_view(entry_detail,
#                                                  get_entry_from_object_id,
#                                                  entry_is_pingable)

urlpatterns = patterns('',
    url(r'^member/(?P<object_id>\d+)/$',
        mk_detail,
        name='mk-detail'),
    url(r'^member/(?P<object_id>\d+)/(?P<slug>[\w\-\"]+)/$',
        mk_detail,
        name='member-detail-with-slug'),
    url(r'^pingback/$',
        default_server,
        name='pingback-server'),
    url(r'^trackback/member/(?P<object_id>\d+)/$',
        MockTrackBackServer(get_mk_entry, mk_is_backlinkable),
        name='trackback-server'),

)
