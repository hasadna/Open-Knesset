from django.conf.urls import url, patterns
from views import PersonListView, PersonDetailView

person_list = PersonListView.as_view()
person_detail = PersonDetailView.as_view()

personsurlpatterns = patterns('',
    url(r'^person/$', person_list, name='person-list'),
    url(r'^person/(?P<pk>\d+)/$', person_detail, name='person-detail'),
)
