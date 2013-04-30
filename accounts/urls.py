#encoding: UTF-8
from django.conf.urls.defaults import url, patterns
from views import send_validation_email, validate_email

urlpatterns = patterns('',
    url(r'^send-validation-email/$', send_validation_email, name='send-validation-email'),
    url(r'^validate-email/(?P<key>.*)/$', validate_email, name='validate-email'),
)
