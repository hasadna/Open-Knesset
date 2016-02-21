# encoding: UTF-8
from django.conf.urls import url, patterns
from ok_tag.views import suggest_tag_post, add_tag_to_object, remove_tag_from_object, \
    add_tag_synonym, TagList, TagDetail, CommitteeMeetingMoreView, untagged_objects

ok_tag_patterns = patterns('',
                           url(r'^tags/(?P<app>\w+)/(?P<object_type>\w+)/(?P<object_id>\d+)/add-tag/$',
                               add_tag_to_object,
                               name='add-tag-to-object'),
                           url(r'^tags/(?P<app>\w+)/(?P<object_type>\w+)/(?P<object_id>\d+)/remove-tag/$',
                               remove_tag_from_object),
                           # disabled for now, because we don't want users to add more tags.
                           # will be added back in the future, but for editors only.
                           # url(r'^tags/(?P<app>\w+)/(?P<object_type>\w+)/(?P<object_id>\d+)/create-tag/$', create_tag_and_add_to_item, name='create-tag'),
                           url(r'^add_tag_synonym/(?P<parent_tag_id>\d+)/(?P<synonym_tag_id>\d+)/$', add_tag_synonym),
                           url(r'^tags/$', TagList.as_view(), name='tags-list'),
                           url(r'^tags/(?P<slug>.*?)/$', TagDetail.as_view(), name='tag-detail'),
                           url(r'^tags_cms/(?P<pk>\d+)/$', CommitteeMeetingMoreView.as_view(),
                               name='tag-detail-more-committees'),
                           url(r'^suggest-tag-post/$', suggest_tag_post, name='suggest-tag-post'),
                           url(r'^untagged/$', untagged_objects, name="untagged-objects"),
                           )
