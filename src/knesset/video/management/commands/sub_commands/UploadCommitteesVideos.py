# encoding: utf-8

import os
from knesset.video.management.commands.sub_commands import SubCommand
from knesset.video.models import Video
from django.contrib.contenttypes.models import ContentType
from knesset.committees.models import Committee
from gdata.youtube.service import YouTubeService
from django.conf import settings
from knesset.video.utils.youtube import UploadYoutubeVideo
from knesset.video.utils import get_videos_queryset

class UploadCommitteesVideos(SubCommand):
    
    def __init__(self,command):
        SubCommand.__init__(self,command)
        videos=self._getVideosToUpload()
        self._debug('got '+str(len(videos))+' videos to upload')
        for video in videos:
            self._check_timer()
            url=video.embed_link
            filename=self._get_data_root()+'committee_mms_videos/'+self._getFilenameFromUrl(url)
            if self._isAlreadyDownloaded(filename):
                self._debug('file ready to be uploaded: '+filename)
                (isOk,ytId)=self._uploadVideo(filename,video)
                if isOk:
                    self._saveVideo(
                        self._getPreParseVideoFields(video,ytId)
                    )
                    self._deleteFile(filename)
                    self._debug('uploaded video')
                else:
                    self._debug('failed to upload video')
            else:
                self._debug('file does not exist: '+filename)
        
    def _deleteFile(self,filename):
        os.remove(filename)
    
    def _getVideoTitleForYoutube(self,video):
        # youtube title is limited to 100 bytes
        pre=u'ישיבת '.encode('utf-8')
        post=(' - '+str(video.published.day)+'/'+str(video.published.month)+'/'+str(video.published.year)).encode('utf-8')
        committee_name=video.content_object.name.encode('utf-8')
        available_length=100-len(pre)-len(post)
        if len(committee_name)>available_length:
            pre=''
            available_length=100-len(post)
            if len(committee_name)>available_length:
                committee_name=committee_name[0:available_length]
        return pre+committee_name+post
        
    
    def _uploadVideo(self,filename,video):
        ret=(False,0)
        if hasattr(video,'title'):
            yts=YouTubeService()
            yts.developer_key=getattr(settings, 'YOUTUBE_DEVELOPER_KEY')
            yts.SetAuthSubToken(getattr(settings, 'YOUTUBE_AUTHSUB_TOKEN'))
            res=UploadYoutubeVideo(
                title=self._getVideoTitleForYoutube(video),
                description=unicode(video.title).encode('utf-8'),
                category='News',
                filename=filename,
                ytService=yts
            )
            if (
                res.isOk and hasattr(res, 'newEntry') and hasattr(res.newEntry, 'id')
                and hasattr(res.newEntry.id, 'text')
            ):
                ret=(True,res.newEntry.id.text)
            else:
                self._warn('failed to upload, invalid res from UploadYoutubeVideo')
                self._warn('msg = '+str(res.errMsg))
                self._warn('desc = '+str(res.errDesc))
        else:
            self._warn('video does not have title ('+filename+')')
        return ret
    
    def _saveVideo(self,videoFields):
        v=Video(**videoFields)
        v.save()
        return v
                
    def _getPreParseVideoFields(self,video,source_id):
        return {
            'title':video.title,
            'source_type':'youtube_pre_parse',
            'source_id':source_id,
            'group':'youtube_upload',
            'content_object':video,
        }
                        
    def _getVideosToUpload(self):
        ret=[]
        videos=self._getAllMmsVideos()
        for video in videos:
            if not self._isVideoAlreadyUploaded(video):
                ret.append(video)
        return ret 

    def _getAllMmsVideos(self):
        object_type=ContentType.objects.get_for_model(Committee)
        return Video.objects.filter(content_type__pk=object_type.id,group='mms').order_by('id')

    def _isVideoAlreadyUploaded(self,video):
        qs=get_videos_queryset(video,group='youtube_upload',ignoreHide=True)
        return qs.count()>0

    def _getFilenameFromUrl(self,url):
        filename=url.split('/')
        filename=filename[len(filename)-1]
        return filename

    def _isAlreadyDownloaded(self,filename):
        return os.path.exists(filename)
    
