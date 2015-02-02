from django.conf.urls import url, patterns, include
from views import PublicUserProfile, ProfileListView, login_view, login_redirect, login_redirect_facebook_canvas, login_redirect_facebook_canvas_complete, login_redirect_facebook_canvas_start

profile_list = ProfileListView.as_view()
user_public_profile = PublicUserProfile.as_view(
    template_name='user/public_profile.html')
user_tagged_items = PublicUserProfile.as_view(
    template_name='user/tagged_items.html')
user_annotated_items = PublicUserProfile.as_view(
    template_name='user/annotated_items.html')
user_followed_topics = PublicUserProfile.as_view(
    template_name='user/followed_topics.html')

# views coded in this app
urlpatterns = patterns(
    'user.views',
    url(r'^create/$', 'create_user', name='register'),
    url(r'^edit-profile/$', 'edit_profile', name='edit-profile'),
    url(r'^follow/$', 'user_follow_unfollow', name='user-follow-unfollow'),
    url(r'^follow-query/$', 'user_is_following', name='user-is-following')
)

# auth views
urlpatterns += patterns(
    'django.contrib.auth.views',
    url(r'^logout/$', 'logout_then_login', name='logout'),
    url(r'^password_reset/$', 'password_reset',
        {'template_name': 'user/password_reset_form.html'},
        name='password_reset'),
    url(r'^password_reset/done/$', 'password_reset_done',
        {'template_name': 'user/password_reset_done.html'},
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'password_reset_confirm',
        {'template_name': 'user/password_reset_confirm.html'},
        name='password_reset_confirm'),
    url(r'^reset/done/$', 'password_reset_complete',
        {'template_name': 'user/password_reset_complete.html'},
        name='password_reset_complete'),
)

urlpatterns += patterns(
    '',
    url(r'^login/$', login_view,
        {'template_name': 'user/login.html'}, name='login'),
    url(r'^login-redirect/(?P<target>[0-9A-Za-z]+)/$', login_redirect),
    url(r'^login-redirect-facebook-canvas/(?P<target>[0-9A-Za-z]+)/$', login_redirect_facebook_canvas),
    url(r'^login-redirect-facebook-canvas-start/(?P<target>[0-9A-Za-z]+)/$', login_redirect_facebook_canvas_start),
    url(r'^login-redirect-facebook-canvas-complete/(?P<target>[0-9A-Za-z]+)/$', login_redirect_facebook_canvas_complete),
    (r'^registration/', include('accounts.urls')),
    url(r'^(?P<pk>\d+)/$', user_public_profile, name='public-profile'),
    url(r'^(?P<pk>\d+)/topic/$', user_followed_topics,
        name='user-followed-topics'),
    url(r'^(?P<slug>.+)/tagged/$', user_tagged_items, name='user-tagged-items'),
    url(r'^(?P<slug>.+)/annotated/$', user_annotated_items,
        name='user-annotated-items'),
    url(r'^(?P<slug>.+)/$', user_public_profile, name='public-profile'),
    url(r'^$', profile_list, name='profile-list'),
)
