from django.conf.urls.defaults import url, patterns
from django.utils.translation import ugettext
from models import Person
from views import PersonListView, PersonDetailView

person_list = PersonListView.as_view()
person_detail = PersonDetailView.as_view()

personsurlpatterns = patterns('',
    url(r'^person/$', person_list, name='person-list'),
    url(r'^person/(?P<pk>\d+)/$', person_detail, name='person-detail'),
)
