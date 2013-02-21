#encoding: UTF-8
from django.conf.urls.defaults import *

from views import *

meetings_list = PlenumMeetingsListView(queryset=CommitteeMeeting.objects.all(), paginate_by=20)

plenumurlpatterns = patterns ('',
	url(r'^plenum/$', PlenumView.as_view(), name='plenum'),
	url(r'^plenum/(?P<pk>\d+)/$', MeetingDetailView.as_view(), name='plenum-meeting'),
	url(r'^plenum/all_meetings/$', meetings_list , {'committee_id':0}, name='plenum-all-meetings'),
)
