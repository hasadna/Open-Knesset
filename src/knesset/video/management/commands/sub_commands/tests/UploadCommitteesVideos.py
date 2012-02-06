#encoding: utf-8

from django.test import TestCase
from knesset.video.management.commands.sub_commands.UploadCommitteesVideos import UploadCommitteesVideos

class UploadCommitteesVideo_test(UploadCommitteesVideos):
    
    def __init__(self,
        testCase,allMmsVideos,isVideoAlreadyUploadedReturn,isAlreadyDownloadedReturn,
        uploadVideoReturn,
    ):
        self._testCase=testCase
        self._allMmsVideos=allMmsVideos
        self._isVideoAlreadyUploadedReturn=isVideoAlreadyUploadedReturn
        self._isAlreadyDownloadedReturn=isAlreadyDownloadedReturn
        self._uploadVideoReturn=uploadVideoReturn
        self.saveVideoLog=[]
        self.deleteFileLog=[]
        UploadCommitteesVideos.__init__(self,None)
        
    def _getAllMmsVideos(self):
        return self._allMmsVideos
    
    def _isVideoAlreadyUploaded(self,video):
        self._testCase.assertIn(video,self._isVideoAlreadyUploadedReturn)
        return self._isVideoAlreadyUploadedReturn[video]

    def _isAlreadyDownloaded(self,filename):
        self._testCase.assertIn(filename,self._isAlreadyDownloadedReturn)
        return self._isAlreadyDownloadedReturn[filename]
    
    def _uploadVideo(self,filename,video):
        self._testCase.assertIn((filename,video),self._uploadVideoReturn)
        return self._uploadVideoReturn[(filename,video)]

    def _saveVideo(self,videoFields):
        self.saveVideoLog.append(videoFields)

    def _deleteFile(self,filename):
        self.deleteFileLog.append(filename)

    def _log(self,*args,**kwargs):
        pass
        #print args[1]
        
    def _check_timer(self,*args,**kwargs): pass
    
    def _get_data_root(self):
        return '/data/'

class Video_test():

    def __init__(self,embed_link,title):
        self.embed_link=embed_link
        self.title=title
        

class testUploadCommitteesVideos(TestCase):
    
    maxDiff=None
    
    def testUploadCommitteesVideos(self):
        videos=[
            Video_test(
                embed_link='mms://1.2.3.4/file1.asf',
                title='video1',
            ),
            Video_test(
                embed_link='mms://1.2.3.4/file2.asf',
                title='video2',
            ),
            Video_test(
                embed_link='mms://1.2.3.4/file3.asf',
                title='video3',
            ),
            Video_test(
                embed_link='mms://1.2.3.4/file4.asf',
                title='video4',
            ),
            Video_test(
                embed_link='mms://1.2.3.4/file5.asf',
                title='video5',
            ),
        ]
        obj=UploadCommitteesVideo_test(
            self,
            allMmsVideos=videos,
            isVideoAlreadyUploadedReturn={
                videos[0]:True,
                videos[1]:False,
                videos[2]:False,
                videos[3]:False,
                videos[4]:False,
            },
            isAlreadyDownloadedReturn={
                '/data/committee_mms_videos/file2.asf':False,
                '/data/committee_mms_videos/file3.asf':True,
                '/data/committee_mms_videos/file4.asf':True,
                '/data/committee_mms_videos/file5.asf':True,
            },
            uploadVideoReturn={
                ('/data/committee_mms_videos/file3.asf',videos[2]):(False,'0'),
                ('/data/committee_mms_videos/file4.asf',videos[3]):(True,'12345'),
                ('/data/committee_mms_videos/file5.asf',videos[4]):(True,'23456'),
            },
        )
        self.assertEqual(obj.saveVideoLog,[
            {
                'content_object':videos[3],
                'group': 'youtube_upload',
                'source_id': '12345',
                'source_type': 'youtube_pre_parse',
                'title': 'video4'
            },
            {
                'content_object':videos[4],
                'group': 'youtube_upload',
                'source_id': '23456',
                'source_type': 'youtube_pre_parse',
                'title': 'video5'
            },
        ])
        self.assertEqual(obj.deleteFileLog,[
            '/data/committee_mms_videos/file4.asf',
            '/data/committee_mms_videos/file5.asf',
        ])






