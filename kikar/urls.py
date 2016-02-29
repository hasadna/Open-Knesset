from django.conf import settings
from django.conf.urls import include, url, patterns
from django.contrib import admin

from kikar import views
urlpatterns = patterns('',
                       url(r'^get-statuses/$', views.get_statuses, name='get-statuses'),
                       url(r'^get-member/(?P<pk>\d+)/$', views.get_member, name='get-member'),
)
