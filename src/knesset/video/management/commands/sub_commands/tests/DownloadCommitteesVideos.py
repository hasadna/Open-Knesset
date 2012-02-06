#encoding: utf-8

from django.test import TestCase
from knesset.video.management.commands.sub_commands.DownloadCommitteesVideos import DownloadCommitteesVideos

class Mms_test:
    
    def __init__(self,parent):
        self._parent=parent
    
    def get_size(self,url):
        return self._parent.mmsGetSize(url)
    
    def resume_download(self,url,partfilename,mins_remaining):
        return self._parent.mmsResumeDownload(url,partfilename,mins_remaining)
    
    def download(self,url,filename,mins_remaining):
        return self._parent.mmsDownload(url,filename,mins_remaining)

class DownloadCommitteesVideos_test(DownloadCommitteesVideos):

    def __init__(
        self,testCase,videosToDownloadReturn,isAlreadyDownloadedReturn,
        getFileSizeReturn,getDownloadedFileSizeReturn,
        mmsGetSizeReturn,mb_quota
    ):
        mms=Mms_test(self)
        self._testCase=testCase
        self._videosToDownloadReturn=videosToDownloadReturn
        self._isAlreadyDownloadedReturn=isAlreadyDownloadedReturn
        self._getFileSizeReturn=getFileSizeReturn
        self._getDownloadedFileSizeReturn=getDownloadedFileSizeReturn
        self._mmsGetSizeReturn=mmsGetSizeReturn
        self.mmsResumeDownloadLog=[]
        self.mmsDownloadLog=[]
        self.renameFileLog=[]
        DownloadCommitteesVideos.__init__(self,command=None,mms=mms,mb_quota=mb_quota)

    def _getVideosToDownload(self):
        return self._videosToDownloadReturn

    def _isAlreadyDownloaded(self,filename):
        self._testCase.assertIn(filename,self._isAlreadyDownloadedReturn)
        return self._isAlreadyDownloadedReturn[filename]

    def _get_data_root(self):
        return '/data/'
    
    def mmsGetSize(self,url):
        self._testCase.assertIn(url,self._mmsGetSizeReturn)
        return self._mmsGetSizeReturn[url]
    
    def _getFileSize(self,filename):
        self._testCase.assertIn(filename,self._getFileSizeReturn)
        return self._getFileSizeReturn[filename]
    
    def mmsResumeDownload(self,url,partfilename,mins_remaining):
        self.mmsResumeDownloadLog.append((url,partfilename,mins_remaining))
        return True

    def mmsDownload(self,url,filename,mins_remaining):
        self.mmsDownloadLog.append((url,filename,mins_remaining))
        return True
        
    def _getDownloadedFileSize(self,filename):
        self._testCase.assertIn(filename,self._getDownloadedFileSizeReturn)
        return self._getDownloadedFileSizeReturn[filename]
    
    def _renameFile(self,filename,newfilename):
        self.renameFileLog.append((filename,newfilename))
    
    def _debug(self,*args,**kwargs):
        pass #print args[0]
        
    def _warn(self,*args,**kwargs):
        pass #print args[0]
        
    def _check_timer(self):
        pass
    
    def _timer_remaining(self):
        return 60
    
    def _verifyDataDir(self):
        pass

class Video_test():
    
    def __init__(self,embed_link):
        self.embed_link=embed_link

class testDownloadCommitteesVideos(TestCase):
    
    maxDiff=None
    
    def testDownloadCommitteesVideos(self):
        videosToDownload=[
            Video_test('mms://1.2.3.4/video1.asf'),
            Video_test('mms://2.3.4.5/video2.asf'),
            Video_test('mms://2.3.4.5/video3.asf'),
            Video_test('mms://2.3.4.5/video4.asf'),
            Video_test('mms://2.3.4.5/video5.asf'),
            Video_test('mms://2.3.4.5/video6.asf'),
            Video_test('mms://2.3.4.5/video7_will_not_be_downloaded_due_to_quota.asf'),
        ]
        isAlreadyDownloaded={
            '/data/committee_mms_videos/video1.asf':True,
            '/data/committee_mms_videos/video2.asf':False,
            '/data/committee_mms_videos/video2.asf.part':True,
            '/data/committee_mms_videos/video3.asf':False,
            '/data/committee_mms_videos/video3.asf.part':True,
            '/data/committee_mms_videos/video4.asf':False,
            '/data/committee_mms_videos/video4.asf.part':True,
            '/data/committee_mms_videos/video5.asf':False,
            '/data/committee_mms_videos/video5.asf.part':False,
            '/data/committee_mms_videos/video6.asf':False,
            '/data/committee_mms_videos/video6.asf.part':False,
        }
        mmsGetSizeReturn={
            'mms://2.3.4.5/video2.asf':260000000,
            'mms://2.3.4.5/video3.asf':260000000,
            'mms://2.3.4.5/video4.asf':260000000,
            'mms://2.3.4.5/video5.asf':260000000,
            'mms://2.3.4.5/video6.asf':260000000,
        }
        getFileSize={
            '/data/committee_mms_videos/video1.asf':260000000,
            '/data/committee_mms_videos/video2.asf.part':260000000,
            '/data/committee_mms_videos/video3.asf.part':260000000,
            '/data/committee_mms_videos/video4.asf.part':1,
        }
        getDownloadedFileSize={
            '/data/committee_mms_videos/video2.asf.part':260000000,
            '/data/committee_mms_videos/video3.asf.part':1,
            '/data/committee_mms_videos/video4.asf.part':260000000,
            '/data/committee_mms_videos/video5.asf.part':259000000,
            '/data/committee_mms_videos/video6.asf.part':260000000,
        }
        mb_quota=260+260+260+250
        obj=DownloadCommitteesVideos_test(
            self,
            videosToDownload,
            isAlreadyDownloaded,
            getFileSize,
            getDownloadedFileSize,
            mmsGetSizeReturn,
            mb_quota
        )
        self.assertEqual(obj.mmsResumeDownloadLog,[
            ('mms://2.3.4.5/video4.asf', '/data/committee_mms_videos/video4.asf.part', 1.0)
        ])
        self.assertEqual(obj.mmsDownloadLog,[
            ('mms://2.3.4.5/video5.asf', '/data/committee_mms_videos/video5.asf.part', 1.0),
            ('mms://2.3.4.5/video6.asf', '/data/committee_mms_videos/video6.asf.part', 1.0),
        ])
        #print obj.renameFileLog
        self.assertEqual(obj.renameFileLog,[
            ('/data/committee_mms_videos/video4.asf.part','/data/committee_mms_videos/video4.asf'),
            ('/data/committee_mms_videos/video5.asf.part','/data/committee_mms_videos/video5.asf'),
            ('/data/committee_mms_videos/video6.asf.part','/data/committee_mms_videos/video6.asf'),
        ])
