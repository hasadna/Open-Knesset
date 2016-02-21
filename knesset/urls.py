from django.conf import settings
from django.conf.urls import include, url, patterns
from django.contrib import admin
from django.views.generic import RedirectView
from django.views.decorators.cache import cache_page
from django.contrib.sitemaps import views as sitemaps_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns, static

from planet import views as planet_views
from hitcount.views import update_hit_count_ajax
from backlinks.trackback.server import TrackBackServer
from backlinks.pingback.server import default_server
from voting.views import vote_on_object

from knesset import feeds
from knesset.sitemap import sitemaps as sitemaps_dict
from mks.urls import mksurlpatterns
from laws.urls import lawsurlpatterns
from committees.urls import committeesurlpatterns
from ok_tag.views import TagList, TagDetail, suggest_tag_post, add_tag_synonym, remove_tag_from_object, \
    add_tag_to_object, untagged_objects
from plenum.urls import plenumurlpatterns
from persons.urls import personsurlpatterns
from mks.views import get_mk_entry, mk_is_backlinkable
from laws.models import Bill

from lobbyists.urls import lobbyistpatterns
from auxiliary.urls import auxiliarysurlpatterns

from auxiliary.views import (
    main, post_annotation, post_details, post_feedback,
    RobotsView, AboutView, CommentsView, help_page)
from ok_tag.urls import ok_tag_patterns

admin.autodiscover()

js_info_dict = {
    'packages': ('knesset',),
}

# monkey patching the planet app
planet_views.post_detail = post_details

urlpatterns = patterns('',
    url(r'^$', main, name='main'),
    (r'^topic/(?P<tail>(.*))', RedirectView.as_view(url='/committee/topic/%(tail)s')),
    url(r'^about/$', AboutView.as_view(), name='about'),
    (r'^robots\.txt$', RobotsView.as_view()),
    (r'^api/', include('apis.urls')),
    (r'^agenda/', include('agendas.urls')),
    (r'^users/', include('user.urls')),
    (r'^kikar/', include('kikar.urls')),
    url('', include('social.apps.django_app.urls', namespace='social')),
    url(r'^help/$', help_page, name="help"),
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/$', CommentsView.as_view()),
    url(r'^comments/delete/(?P<comment_id>\d+)/$', 'knesset.utils.delete', name='comments-delete-comment'),
    url(r'^comments/post/', 'knesset.utils.comment_post_wrapper', name='comments-post-comment'),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    #(r'^search/', include('haystack.urls')),
    url(r'^search/', 'auxiliary.views.search', name='site-search'),
    url(r'^feeds/$', feeds.MainActionsFeed(), name='main-actions-feed'),
    url(r'^feeds/comments/$', feeds.Comments(),name='feeds-comments'),
    url(r'^feeds/votes/$', feeds.Votes(),name='feeds-votes'),
    url(r'^feeds/bills/$', feeds.Bills(),name='feeds-bills'),
    (r'^feeds/annotations/$', feeds.Annotations()),
    #(r'^sitemap\.xml$', redirect_to, {'url': '/static/sitemap.xml'}),
    url(r'^sitemap\.xml$',
        cache_page(settings.LONG_CACHE_TIME)(sitemaps_views.index),
        {'sitemaps': sitemaps_dict, 'sitemap_url_name': 'sitemaps'},
        name='sitemap'),
    url(r'^sitemap-(?P<section>.+)\.xml$',
        cache_page(settings.LONG_CACHE_TIME)(sitemaps_views.sitemap),
        {'sitemaps': sitemaps_dict},
        name='sitemaps'),
    (r'^planet/', include('planet.urls')),
    url(r'^ajax/hit/$', update_hit_count_ajax, name='hitcount_update_ajax'),
    (r'^annotate/write/$', post_annotation, {}, 'annotatetext-post_annotation'),
    (r'^annotate/', include('annotatetext.urls')),
    (r'^avatar/', include('avatar.urls')),
    url(r'^pingback/', default_server, name='pingback-server'),
    url(r'^trackback/member/(?P<object_id>\d+)/$', TrackBackServer(get_mk_entry, mk_is_backlinkable), name='member-trackback'),
    (r'^act/', include('actstream.urls')),

    url(r'^uservote/bill/(?P<object_id>\d+)/(?P<direction>\-?\d+)/?$',
        vote_on_object, dict(
            model=Bill, template_object_name='bill',
            template_name='laws/bill_confirm_vote.html',
            allow_xmlhttprequest=True),
        name='vote-on-bill'),
    (r'^video/', include('video.urls')),
    (r'^mmm-documents/', include('mmm.urls')),
    (r'^event/', include('events.urls')),
    (r'^tinymce/', include('tinymce.urls')),
    (r'^suggestions/', include('suggestions.urls')),
    url(r'^feedback/', post_feedback, name="feedback-post"),
    # url(r'^untagged/$', untagged_objects, name="untagged-objects"),
)


urlpatterns += ok_tag_patterns
urlpatterns += mksurlpatterns + lawsurlpatterns + committeesurlpatterns + plenumurlpatterns + lobbyistpatterns
urlpatterns += staticfiles_urlpatterns() + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# polyorg patterns are removed right now, the cache handling on it's views
# seems broken, specially when trying to cache querysets
# urlpatterns += polyorgurlpatterns + personsurlpatterns
urlpatterns += personsurlpatterns
urlpatterns += auxiliarysurlpatterns

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += patterns('',
                            url(r'^__debug__/', include(debug_toolbar.urls)),
                            )
