from django.conf.urls.defaults import *
from views import BadgeTypeDetailView, BadgeTypeListView


detail_view = BadgeTypeDetailView.as_view()
list_view = BadgeTypeListView.as_view()
urlpatterns = patterns('',
    url(r'^$', BadgeTypeListView.as_view(), name='all-badge-list'),
    url(r'^(?P<pk>\d+)/$', BadgeTypeDetailView.as_view(), name='badge-detail'),
)
