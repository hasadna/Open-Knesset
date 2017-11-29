# encoding: UTF-8
from django.conf.urls import url, patterns
from djangoratings.views import AddRatingFromModel
from views import (
    MeetingsListView, MeetingDetailView, MeetingTagListView,
    CommitteeListView, CommitteeDetailView, TopicListView, TopicsMoreView,
    TopicDetailView, delete_topic, delete_topic_rating, meeting_list_by_date,
    edit_topic, CommitteeMMMDocuments, UnpublishedProtocolslistView, FutureMeetingslistView,
    static_committee_detail_redirect, static_committee_redirect, static_committee_meeting_redirect
)


meetings_list = MeetingsListView.as_view()
unpublished_protocols_list = UnpublishedProtocolslistView.as_view()
future_meetings_list = FutureMeetingslistView.as_view()





committeesurlpatterns = patterns('',
                                 url(r'^committee/$', static_committee_redirect('committees/index.html'),
                                     name='committee-list'),
                                 url(r'^committee/(?P<pk>\d+)/$', static_committee_detail_redirect(),
                                     name='committee-detail'),
                                 url(r'^committee/all_meetings/$', static_committee_redirect('committees/index.html'),
                                     name='committee-all-meetings'),
                                 url(r'^committee/(?P<pk>\d+)/all_meetings/$', static_committee_detail_redirect(),
                                     name='committee-all-meetings'),
                                 url(r'^committee/(?P<pk>\d+)/all_unpublished_protocols/$',
                                     static_committee_detail_redirect(), name='committee-all-unpublished-protocols'),
                                 url(r'^committee/(?P<pk>\d+)/all_future_meetings/$',
                                     static_committee_detail_redirect(), name='committee-all-future-meetings'),
                                 url(r'^committee/date/(?P<date>[\d\-]+)/$',
                                     static_committee_redirect('committees/index.html'), name='committee-meetings-by-date'),
                                 url(r'^committee/(?P<pk>\d+)/date/(?P<date>[\d\-]+)/$',
                                     static_committee_detail_redirect(), name='committee-meetings-by-date'),
                                 url(r'^committee/(?P<pk>\d+)/date/$',
                                     static_committee_detail_redirect(), name='committee-meetings-by-date'),
                                 url(r'^committee/(?P<pk>\d+)/topic/$',
                                     static_committee_detail_redirect(), name='committee-topic-list'),
                                 url(r'^committee/meeting/(?P<pk>\d+)/$', static_committee_meeting_redirect(),
                                     name='committee-meeting'),
                                 url(r'^committee/(?P<pk>\d+)/mmm_documents/$',
                                     static_committee_detail_redirect(), name='committee-mmm-documents-list'),
                                 url(r'^committee/(?P<pk>\d+)/mmm_documents/date/(?P<date>[\d\-]+)/$',
                                     static_committee_detail_redirect(),
                                     name='committee-mmm-documents-list-by-date'),
                                 )
