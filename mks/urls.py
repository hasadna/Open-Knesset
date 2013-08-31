from django.conf.urls import url, patterns
from . import views as mkv
from feeds import MemberActivityFeed
from django.views.decorators.cache import cache_page

cached = cache_page(60 * 15)

mksurlpatterns = patterns('mks.views',
    url(r'^parties-members/$', cached(mkv.PartiesMembersRedirctView.as_view()), name='parties-members-index'),
    url(r'^parties-members/(?P<pk>\d+)/$', cached(mkv.PartiesMembersPicturesView.as_view()), name='parties-members-list'),
    url(r'^parties-members/(?P<pk>\d+)/raw$', mkv.PartiesMembersRawView.as_view(), name='parties-members-list-raw'),
    url(r'^member/$', cached(mkv.MemberRedirectView.as_view()), name='member-list'),
    url(r'^member/csv$', mkv.MemberCsvView.as_view()),
    url(r'^party/csv$', mkv.PartyCsvView.as_view()),
    url(r'^member/(?P<pk>\d+)/$', 'mk_detail', name='member-detail'),

    # "more" actions
    url(r'^member/(?P<pk>\d+)/more_actions/$', mkv.MemeberMoreActionsView.as_view(), name='member-more-actions'),
    url(r'^member/(?P<pk>\d+)/more_legislation/$', mkv.MemeberMoreLegislationView.as_view(), name='member-more-legislation'),
    url(r'^member/(?P<pk>\d+)/more_committee/$', mkv.MemeberMoreCommitteeView.as_view(), name='member-more-committees'),
    url(r'^member/(?P<pk>\d+)/more_mmm/$', mkv.MemeberMoreMMMView.as_view(), name='member-more-mmm'),

    url(r'^member/(?P<object_id>\d+)/rss/$', MemberActivityFeed(), name='member-activity-feed'),
    url(r'^member/(?P<pk>\d+)/(?P<slug>[\w\-\"]+)/$', 'mk_detail', name='member-detail-with-slug'),
    # TODO:the next url is hardcoded in a js file
    url(r'^member/auto_complete/$', mkv.member_auto_complete, name='member-auto-complete'),
    url(r'^member/search/?$', mkv.member_by_name, name='member-by-name'),
    url(r'^member/by/(?P<stat_type>' + '|'.join(x[0] for x in mkv.MemberListView.pages) + ')/$', cached(mkv.MemberListView.as_view()), name='member-stats'),

    url(r'^party/$',  cached(mkv.PartyRedirectView.as_view()), name='party-list'),
    url(r'^party/(?P<pk>\d+)/$', cached(mkv.PartyDetailView.as_view()), name='party-detail'),
    url(r'^party/(?P<pk>\d+)/(?P<slug>[\w\-\"]+)/$', cached(mkv.PartyDetailView.as_view()), name='party-detail-with-slug'),
    url(r'^party/by/(?P<stat_type>' + '|'.join(x[0] for x in mkv.PartyListView.pages) + ')/$', cached(mkv.PartyListView.as_view()), name='party-stats'),
    url(r'^party/search/?$', mkv.party_by_name, name='party-by-name'),
)
