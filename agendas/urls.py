#encoding: UTF-8
from django.conf.urls.defaults import url, patterns
from django.utils.translation import ugettext
from django.views.generic.base import TemplateView

from models import Agenda
from views import AgendaListView
from views import AgendaDetailView
from views import AgendaMkDetailView
from views import AgendaDetailEditView
from views import AgendaVoteDetailView
from views import AgendaVotesMoreView
from views import AgendaBillDetailView
from views import AgendaBillsMoreView
from views import AgendaMeetingDetailView
from views import AgendaMeetingsMoreView
from views import agenda_add_view
from views import update_editors_agendas

agenda_list_view            = AgendaListView(queryset = Agenda.objects.all(),paginate_by=0, extra_context={'title':ugettext('Agendas')})
agenda_detail_view          = AgendaDetailView.as_view()
agenda_mk_detail_view       = AgendaMkDetailView.as_view()
agenda_detail_edit_view     = AgendaDetailEditView.as_view()
agenda_vote_detail_view     = AgendaVoteDetailView.as_view()
agenda_bill_detail_view     = AgendaBillDetailView.as_view()
agenda_meeting_detail_view  = AgendaMeetingDetailView.as_view()


urlpatterns = patterns('',
    url(r'^$', agenda_list_view, name='agenda-list'),
    url(r'^(?P<pk>\d+)/$', agenda_detail_view, name='agenda-detail'),
    url(r'^(?P<pk>\d+)/more-votes/$', AgendaVotesMoreView.as_view(), name='agenda-detail-more-votes'),
    url(r'^(?P<pk>\d+)/more-bills/$', AgendaBillsMoreView.as_view(), name='agenda-detail-more-bills'),
    url(r'^(?P<pk>\d+)/more-meetings/$', AgendaMeetingsMoreView.as_view(), name='agenda-detail-more-meetings'),
    url(r'^(?P<pk>\d+)/member/(?P<member_id>\d+)/$', agenda_mk_detail_view, name='mk-agenda-detail'),
    url(r'^(?P<pk>\d+)/edit/$', agenda_detail_edit_view, name='agenda-detail-edit'),
    url(r'^vote/(?P<pk>\d+)/$', agenda_vote_detail_view, name='agenda-vote-detail'),
    url(r'^bill/(?P<pk>\d+)/$', agenda_bill_detail_view, name='agenda-bill-detail'),
    url(r'^meeting/(?P<pk>\d+)/$', agenda_meeting_detail_view, name='agenda-meeting-detail'),
    url(r'^add/$', agenda_add_view, name='agenda-add'),
    url(r'^update/votes/$', update_editors_agendas, name='update-editors-agendas'),
    url(r'^embed/$', TemplateView.as_view(template_name='agendas/agenda-widget.html'), name="agenda-embed"),
#    url(r'^user/(?P<user_id>\d+)/$', user_agendas_list_view, name),
#    url(r'^vote/(?P<vote_id>\d+)/$', ascribe_agenda_to_vote),
)
