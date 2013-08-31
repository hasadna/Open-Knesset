#encoding: UTF-8
from django.conf.urls import url, patterns
from django.views.decorators.cache import cache_page

cached = cache_page(60 * 15)

from views import PlenumMeetingsListView, PlenumView
from committees.models import CommitteeMeeting
from committees.views import MeetingDetailView

meetings_list = PlenumMeetingsListView.as_view(
    queryset=CommitteeMeeting.objects.all(), paginate_by=20)

plenumurlpatterns = patterns ('',
	url(r'^plenum/$', cached(PlenumView.as_view()), name='plenum'),
	url(r'^plenum/(?P<pk>\d+)/$', cached(MeetingDetailView.as_view()), name='plenum-meeting'),
	url(r'^plenum/all_meetings/$', cached(meetings_list), {'committee_id':0}, name='plenum-all-meetings'),
)
