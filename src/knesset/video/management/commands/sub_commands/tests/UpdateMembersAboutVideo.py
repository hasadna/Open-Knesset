#encoding: utf-8

import datetime
from django.test import TestCase
from knesset.video.management.commands.sub_commands.UpdateMembersAboutVideo import UpdateMembersAboutVideo

class UpdateMembersAboutVideo_test(UpdateMembersAboutVideo):
    
    def __init__(self,members,testCase,getYoutubeVideosReturn,getVideosReturn):
        self._testCase=testCase
        self._getYoutubeVideosReturn=getYoutubeVideosReturn
        self._getVideosReturn=getVideosReturn
        self.saveVideoLog=[]
        self.hideRelatedVideoLog=[]
        self.hideAboutVideosLog=[]
        UpdateMembersAboutVideo.__init__(self,None,members=members)
    
    def _getYoutubeVideos(self,**kwargs):
        self._testCase.assertEquals(sorted(kwargs.keys()),['q'])
        params=(kwargs['q'])
        self._testCase.assertIn(params,self._getYoutubeVideosReturn)
        return self._getYoutubeVideosReturn[params]
    
    def _getVideos(self, getVideosQuerysetParams, filterParams):
        self._testCase.assertEquals(sorted(getVideosQuerysetParams.keys()), ['ignoreHide','obj'])
        self._testCase.assertEquals(sorted(filterParams.keys()), ['source_id','source_type'])
        params=(
            getVideosQuerysetParams['ignoreHide'], getVideosQuerysetParams['obj'],
            filterParams['source_id'], filterParams['source_type']
        )
        self._testCase.assertIn(params,self._getVideosReturn)
        return self._getVideosReturn[params]
    
    def _saveVideo(self,videoFields):
        self.saveVideoLog.append(videoFields)
        
    def _hideRelatedVideo(self,video):
        self.hideRelatedVideoLog.append(video)

    def _hideMemberAboutVideos(self,member):
        self.hideAboutVideosLog.append(member)

    def _log(self,*args,**kwargs): pass
    
    def _check_timer(self,*args,**kwargs): pass

class Member_test():
    
    def __init__(self,names=[]):
        self.name=names[0]
        self.names=names
        
class Video_test():
    
    def __init__(self, **kwargs):
        video=getDbVideo(**kwargs)
        if 'hide' not in video:
            video['hide']=False
        if 'sticky' not in video:
            video['sticky']=False
        for k in video:
            setattr(self,k,video[k])
    
def getSourceVideo(**kwargs):
    video={
        'id':None, 
        'title':None,
        'embed_url_autoplay':'', 'thumbnail480x360':'',
        'description':'', 'link':'', 
        'published':datetime.datetime(2011,12,01),
    }
    for k in kwargs:
        video[k]=kwargs[k]
    return video

def getDbVideo(**kwargs):
    video={
        'embed_link': '', 'image_link': '', 'source_type': 'youtube', 'link': '', 
        'description': '', 'title': None, 'source_id': None, 
        'group': 'about', 'content_object': None, 'published': ''
    }
    for k in kwargs:
        video[k]=kwargs[k]
    return video

class testUpdateMembersAboutVideo(TestCase):
    
    maxDiff=None
    
    def testUpdateMembersAboutVideo(self):
        kartisBikur=u'כרטיס ביקור ערוץ הכנסת '
        heName2=u'עוד חברכ'
        members=[
            Member_test(['tester testee','testee tester']),
            Member_test(['im the hak']),
            Member_test(['xxx',heName2]),
            Member_test(['zzz']),
        ]
        getYoutubeVideosReturn={
            (kartisBikur+'tester testee'):[
                getSourceVideo(
                    id=1, title=kartisBikur+'tester testee', 
                    published=datetime.datetime(2011,11,01)
                ),
            ],
            (kartisBikur+'testee tester'):[
                getSourceVideo(
                    id=2, title=kartisBikur+'testee tester', 
                    published=datetime.datetime(2011,12,01)
                ),
            ],
            (kartisBikur+'im the hak'):[
                getSourceVideo(id=3, title=kartisBikur+'im the hak', published=None),
                getSourceVideo(
                    id=4, title='im the hak',
                    published=datetime.datetime(2011,12,01)
                ),
                getSourceVideo(
                    id=4, title=kartisBikur,
                    published=datetime.datetime(2011,11,01)
                ),
                getSourceVideo(
                    id=5, title=kartisBikur+'im the hak',
                    published=datetime.datetime(2011,10,01)
                ),
            ],
            (kartisBikur+'xxx'):[getSourceVideo(id=6, title='')],
            (kartisBikur+heName2):[getSourceVideo(id=7, title='')],
            (kartisBikur+'zzz'):[getSourceVideo(id=8,title='zzz',description=kartisBikur)],
        }
        getVideosReturn={
            (True,members[0],2,'youtube'):[],
            (True,members[1],5,'youtube'):[
                Video_test(group='xxx'),
                Video_test(group='related', hide=True),
                Video_test(group='related', sticky=True),
                Video_test(group='related', hide=True, sticky=True),
                Video_test(group='related'),
                Video_test(group='related'),
            ],
            (True,members[3],8,'youtube'):[]
        }
        obj=UpdateMembersAboutVideo_test(members,self,getYoutubeVideosReturn,getVideosReturn)
        self.assertEqual(obj.saveVideoLog,[
            getDbVideo(
                title=kartisBikur+'testee tester', source_id=2, content_object=members[0],
                published=datetime.datetime(2011,12,01)
            ),
            getDbVideo(
                title=kartisBikur+'im the hak', source_id=5, content_object=members[1],
                published=datetime.datetime(2011,10,01)
            ),
            getDbVideo(
                title='zzz', description=kartisBikur, source_id=8, content_object=members[3],
                published=datetime.datetime(2011,12,1)
            )
        ])
        self.assertEqual(obj.hideRelatedVideoLog,[
            getVideosReturn[(True,members[1],5,'youtube')][4]
        ])
        self.assertEqual(obj.hideAboutVideosLog,[
            members[0],
            members[1],
            members[3],
        ])
