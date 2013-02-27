from django.conf import settings
from django.conf.urls.defaults import *
from . import views

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$', views.EventDetailView.as_view(), name='event-detail'),
)
