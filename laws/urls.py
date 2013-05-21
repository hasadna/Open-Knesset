#encoding: UTF-8
from django.conf.urls.defaults import url, patterns
from django.utils.translation import ugettext
from django.views.generic import RedirectView
from hashnav import ListView
from models import Vote, Bill
from views import VoteListView, VoteCsvView, VoteDetailView, VoteTagsView
from views import BillListView, BillCsvView, BillDetailView, BillTagsView
from views import bill_unbind_vote, bill_auto_complete
from views import bill_tags_cloud, embed_bill_details
from views import vote_tags_cloud, vote_auto_complete
import feeds

vote_view = VoteListView(queryset = Vote.objects.all(),paginate_by=20, extra_context={'votes':True,'title':ugettext('Votes')})
bill_list_view = BillListView(queryset=Bill.objects.all().filter(law__merged_into=None).order_by('-stage_date'), paginate_by=20,extra_context={'title':ugettext('Bills')})
bill_detail_view = BillDetailView.as_view()
vote_list_view = VoteListView(queryset = Vote.objects.all(),paginate_by=20, extra_context={'votes':True,'title':ugettext('Votes')})
vote_detail_view = VoteDetailView.as_view()

lawsurlpatterns = patterns ('',
    url(r'^bill/$', bill_list_view, name='bill-list'),
    url(r'^bill/tag/$', bill_tags_cloud, name='bill-tags-cloud'),
    url(r'^bill/rss/$', feeds.Bills(), name='bills-feed'),
    url(r'^bill/csv/$', BillCsvView.as_view()),
    url(r'^bill/tag/(?P<tag>.*)/$', BillTagsView.as_view(), name='bill-tag'),
    url(r'^bill/knesset-booklet/(?P<booklet_num>\d+)/$', RedirectView.as_view(
        url='/bill/?booklet=%(booklet_num)s', permanent=True)),
    url(r'^bill/(?P<pk>\d+)/$', bill_detail_view, name='bill-detail'),
    url(r'^bill/(?P<object_id>\d+)/embed/$', embed_bill_details, name='embed-bill-details'),
    url(r'^bill/(?P<object_id>\d+)/unbind-vote/(?P<vote_id>\d+)/$',
        bill_unbind_vote, name='bill-unbind-vote'),
    url(r'^bill/auto_complete/$', bill_auto_complete, name='bill-auto-complete'),
    url(r'^bill/(?P<slug>[\w\-\"]+)/(?P<pk>\d+)/$', bill_detail_view, name='bill-detail-with-slug'),
    url(r'^vote/$', vote_list_view, name='vote-list'),
    url(r'^vote/csv/$', VoteCsvView.as_view()),
    url(r'^vote/tag/$', vote_tags_cloud, name='vote-tags-cloud'),
    url(r'^vote/rss/$', feeds.Votes(), name='votes-feed'),
    url(r'^vote/tag/(?P<tag>.*)/$', VoteTagsView.as_view(), name='vote-tag'),
    url(r'^vote/(?P<pk>\d+)/$', vote_detail_view, name='vote-detail'),
    url(r'^vote/(?P<object_id>\d+)/$', vote_view, name='vote-detail'),
    # TODO:the next url is hardcoded in a js file
    url(r'^vote/auto_complete/$', vote_auto_complete, name='vote-auto-complete'),
)
