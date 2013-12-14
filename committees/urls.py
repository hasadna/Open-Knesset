#encoding: UTF-8
from django.conf.urls import url, patterns
from djangoratings.views import AddRatingFromModel

from .models import CommitteeMeeting
from views import (
    MeetingsListView, MeetingDetailView, MeetingTagListView,
    CommitteeListView, CommitteeDetailView, TopicListView, TopicsMoreView,
    TopicDetailView, delete_topic, delete_topic_rating, meeting_list_by_date,
    edit_topic)


meetings_list = MeetingsListView.as_view()

committeesurlpatterns = patterns('',
    url(r'^committee/$', CommitteeListView.as_view(), name='committee-list'),
    url(r'^committee/more-topics/$', TopicsMoreView.as_view(), name='committee-topics-more'),
    url(r'^committee/(?P<pk>\d+)/$', CommitteeDetailView.as_view(), name='committee-detail'),
    url(r'^committee/all_meetings/$', meetings_list, name='committee-all-meetings'),
    url(r'^committee/(?P<committee_id>\d+)/all_meetings/$', meetings_list, name='committee-all-meetings'),
    url(r'^committee/date/(?P<date>[\d\-]+)/$', meeting_list_by_date, name='committee-meetings-by-date'),
    url(r'^committee/(?P<committee_id>\d+)/date/(?P<date>[\d\-]+)/$', meeting_list_by_date, name='committee-meetings-by-date'),
    url(r'^committee/(?P<committee_id>\d+)/date/$', meeting_list_by_date, name='committee-meetings-by-date'),
    url(r'^committee/(?P<committee_id>\d+)/topic/$', TopicListView.as_view(), name='committee-topic-list'),
    url(r'^committee/(?P<committee_id>\d+)/topic/add/$',
        edit_topic,
        name='edit-committee-topic'),
    url(r'^committee/(?P<committee_id>\d+)/topic/edit/(?P<topic_id>\d+)/$',
        edit_topic,
        name='edit-committee-topic'),
    url(r'^committee/meeting/(?P<pk>\d+)/$', MeetingDetailView.as_view(), name='committee-meeting'),
    url(r'^committee/meeting/tag/(?P<tag>.*)/$', MeetingTagListView.as_view(),
        name='committeemeeting-tag'),
    url(r'^committee/topic/$', TopicListView.as_view(), name='topic-list'),
    url(r'^committee/topic/(?P<pk>\d+)/delete/$', delete_topic,
        name='delete-committee-topic'),
    url(r'^committee/topic/(?P<pk>\d+)/$', TopicDetailView.as_view(), name='topic-detail'),
    url(r'^committee/topic/(?P<object_id>\d+)/(?P<score>\d+)/$',
        AddRatingFromModel(),
        {'app_label': 'committees', 'model': 'topic', 'field_name': 'rating'},
        name='rate-topic'),
    url(r'^committee/topic/(?P<object_id>\d+)/null/$', delete_topic_rating,
        name='delete-topic-rating'),
)
