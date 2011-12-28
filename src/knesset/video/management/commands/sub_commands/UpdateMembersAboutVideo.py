# encoding: utf-8
from knesset.mks.models import Member
from knesset.video.utils import get_videos_queryset
from knesset.video.utils.youtube import GetYoutubeVideos
from knesset.video.management.commands.sub_commands import SubCommand
from knesset.video.utils.parse_dict import validate_dict
from knesset.video.models import Video

class UpdateMembersAboutVideo(SubCommand):

    def __init__(self,command,members=None):
        SubCommand.__init__(self,command)
        if members is None: members=Member.objects.all()
        for member in members:
            self._debug(member.name)
            self._check_timer()
            sourceVideos=self._fetchSourceVideosOrderedByPublishedDesc(member)
            for sourceVideo in sourceVideos:
                if self._isValidSourceVideo(sourceVideo,member):
                    videos=self._getVideosFromSource(sourceVideo,member)
                    if len(videos)==0:
                        # the source video does not exist in our database
                        # this is the about video for this member!
                        self._updateMemberAboutVideo(sourceVideo,member)
                        break
                    else:
                        # got some videos that match the source video
                        # check if any of them are 'related' videos
                        relatedVideo=None
                        for video in videos:
                            if video.group=='related' and not video.sticky and not video.hide:
                                relatedVideo=video
                                break
                        if relatedVideo is not None:
                            # got a related video that is not sticky and not hidden
                            # hide it in the related and create it again as about
                            # (we could just change the video's group field
                            #  but it's better to create it again to make sure
                            #  it's got all the relevant data)
                            self._hideRelatedVideo(relatedVideo)
                            self._updateMemberAboutVideo(sourceVideo,member)
                        else:
                            break

    def _fetchSourceVideosOrderedByPublishedDesc(self,member):
        videos=[]
        for name in member.names:
            for video in self._fetchSourceVideos(name):
                if validate_dict(video,['published']):
                    videos.append(video)
        return sorted(videos,key=lambda video: video['published'], reverse=True)
    
    def _fetchSourceVideos(self,name):
        return self._getYoutubeVideos(q=u"כרטיס ביקור ערוץ הכנסת "+name)
        
    def _isValidSourceVideo(self,video,member):
        ans=False
        if validate_dict(video,[
            'title','embed_url_autoplay','thumbnail480x360',
            'id','description','link','published'
        ]):
            titledesc=video['title']+video['description']
            if (
                u'כרטיס ביקור' in titledesc
                and u'ערוץ הכנסת' in titledesc
            ):
                for name in member.names:
                    if name in titledesc:
                        ans=True
                        break
        return ans
    
    def _getVideosFromSource(self,sourceVideo,member):
        return self._getVideos(
            getVideosQuerysetParams={'obj':member, 'ignoreHide':True},
            filterParams={'source_id':sourceVideo['id'],'source_type':'youtube'}
        )
        
    def _updateMemberAboutVideo(self,sourceVideo,member):
        self._hideMemberAboutVideos(member)
        self._saveVideo({
            'embed_link':sourceVideo['embed_url_autoplay'],
            'image_link':sourceVideo['thumbnail480x360'],
            'title':sourceVideo['title'],
            'description':sourceVideo['description'],
            'link':sourceVideo['link'],
            'source_type':'youtube', 
            'source_id':sourceVideo['id'],
            'published':sourceVideo['published'],
            'group':'about', 
            'content_object':member
        })

    # the following functions perform low level operations that will not be performed when testing
    # e.g. saving database data or fetching from remote sites

    def _getYoutubeVideos(self,**kwargs):
        return GetYoutubeVideos(**kwargs).videos
    
    def _getVideos(self, getVideosQuerysetParams, filterParams):
        return get_videos_queryset(**getVideosQuerysetParams).filter(**filterParams)
    
    def _saveVideo(self,videoFields):
        v=Video(**videoFields)
        v.save()
        
    def _hideRelatedVideo(self,video):
        video.hide=True
        video.save()
        
    def _hideMemberAboutVideos(self,member):
        videos=get_videos_queryset(member,group='about')
        for video in videos:
            video.hide=True
            video.save()
