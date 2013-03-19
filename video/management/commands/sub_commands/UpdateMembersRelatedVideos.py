# encoding: utf-8

from video.management.commands.sub_commands import SubCommand
from video.utils.youtube import GetYoutubeVideos
from mks.models import Member
from video.utils.parse_dict import validate_dict
from video.utils import get_videos_queryset
from video.models import Video

class UpdateMembersRelatedVideos(SubCommand):

    def __init__(self,command,members=None,only_current_knesset=False,member_ids=[]):
        SubCommand.__init__(self,command)
        if members is None:
            if len(member_ids)>0:
                members=Member.objects.filter(id__in=member_ids)
            elif only_current_knesset is True:
                members=Member.current_knesset.filter(is_current=True)
                self._debug('only current knesset')
            else:
                members=Member.objects.all()
        self._debug('updating related videos for '+str(len(members))+' members')
        for member in members:
            self._debug(member.name)
            self._check_timer()
            relvids=[]
            for name in member.names:
                self._debug(name)
                for video in self._getVideosForMember(name):
                    if self._verify_related_video(video,name):
                        relvids.append(video)
            if len(relvids)>0:
                for video in relvids:
                    self._update_member_related_video(member,video)

    def _getVideosForMember(self,name):
        return self._getYoutubeVideos(q='"'+name+'"',max_results=15,limit_time='this_month')

    def _getYoutubeVideos(self,**kwargs):
        return GetYoutubeVideos(**kwargs).videos

    def _verify_related_video(self,video,name):
        if validate_dict(video,['title','description']):
            titledesc=video['title'] #+video['description']
            if (
                validate_dict(video,['embed_url_autoplay','thumbnail90x120','id','link','published'])
                and name in titledesc
                and video['published'] is not None
            ):
                return True
            else:
                return False
        else:
            return False

    def _getVideoFields(self,video,member):
        return {
            'embed_link':video['embed_url_autoplay'],
            'small_image_link':video['thumbnail90x120'],
            'title':video['title'],
            'description':video['description'],
            'link':video['link'],
            'source_type':'youtube',
            'source_id':video['id'],
            'published':video['published'],
            'group':'related',
            'content_object':member
        }

    def _isMemberHaveVideo(self,member,video):
        return self._getMemberExistingVideosCount(
            ignoreHide=True, member=member,
            source_id=video['id'],
            source_type='youtube',
        )>0

    def _getMemberExistingVideosCount(self,ignoreHide,member,source_id,source_type):
        qs=get_videos_queryset(member,ignoreHide=ignoreHide)
        qs=qs.filter(source_id=source_id,source_type=source_type)
        return qs.count()

    def _saveVideo(self,videoFields):
        v=Video(**videoFields)
        v.save()

    def _update_member_related_video(self,member,video):
        if not self._isMemberHaveVideo(member, video):
            self._saveVideo(self._getVideoFields(video, member))
