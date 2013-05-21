from django.conf import settings
from django.conf.urls.defaults import url, patterns
from views import EventDetailView, MoreUpcomingEventsView

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$', EventDetailView.as_view(), name='event-detail'),
    url(r'^more_upcoming/$', MoreUpcomingEventsView.as_view(), name='more-upcoming-events'),
)
