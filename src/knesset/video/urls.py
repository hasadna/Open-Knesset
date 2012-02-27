#encoding: UTF-8
from django.conf.urls.defaults import patterns, url
from django.utils.translation import ugettext
from models import Video
from views import VideoListView, videoListApproveAjaxView

video_list_view = VideoListView(
    queryset = Video.objects.all().order_by('reviewed','-published'),
    paginate_by=50,
    extra_context={'title':ugettext('Videos')}
)

urlpatterns = patterns('',
    url(r'^$', video_list_view, name='video-list'),
    url(r'^approve_ajax/', videoListApproveAjaxView),
)
