# encoding: utf-8

from knesset.video.management.commands.sub_commands import SubCommand
from knesset.committees.models import Committee
from BeautifulSoup import BeautifulSoup
import urllib,re,datetime,traceback,sys
from knesset.video.utils import get_videos_queryset
from knesset.video.models import Video

class UpdateCommitteesVideos(SubCommand):

    PORTAL_KNESSET_COMMITTEES_INDEX_PAGE_URL='http://www.knesset.gov.il/committees/heb/current_vaadot.asp'
    
    PORTAL_KNESSET_BASEHREF='http://portal.knesset.gov.il'
    
    KNESSET_BASEHREF='http://www.knesset.gov.il'
    
    KNESSET_BASEHREFPATH='http://www.knesset.gov.il/committees/heb/'

    def __init__(self,command,committees=None):
        SubCommand.__init__(self,command)
        if self._get_opt('with-history'):
            self._error('download of historical data is not supported yet')
        if committees is None:
            if self._get_opt('committee-id') is not None:
                committees=[Committee.objects.get(id=self._get_opt('committee-id'))]
            else:
                committees=Committee.objects.all()
        for comm in committees:
            self._debug('UpdateCommitteesVideos - '+str(comm.id)+': '+comm.name)
            self._check_timer()
            broadcasts_url=comm.portal_knesset_broadcasts_url
            if len(broadcasts_url)==0:
                self._debug('committee does not have a broadcasts url, trying to find one')
                broadcasts_url=self._update_committee_broadcasts_url(comm)
            if len(broadcasts_url)>0:
                self._debug('got a broadcasts url - '+str(broadcasts_url))
                self._debug('searching for videos in the broadcasts url')
                videos=self._get_committee_videos(broadcasts_url)
                self._debug('got '+str(len(videos))+' videos')
                for video in videos:
                    self._update_committee_mms_video(comm,video)
            else:
                self._warn('could not find a broadcasts url')

    def _get_committees_index_page(self):
        self._debug('fetching committee index page from '+self.PORTAL_KNESSET_COMMITTEES_INDEX_PAGE_URL)
        try:
            rf=urllib.urlopen(self.PORTAL_KNESSET_COMMITTEES_INDEX_PAGE_URL)
            return rf.read().decode('windows-1255').encode('utf-8')
        except Exception, e:
            self._warn('could not fetch committees_index_page, exception: '+str(e))
            traceback.print_exc(file=sys.stdout)
            return ''
        
    def _get_committee_mainpage(self,soup,name):
        ret=['','']
        try:
            href=''
            names=[name,name.replace(' ','  ')]
            for name in names:
                self._debug('_get_committee_mainpage - '+unicode(name))
                elt=soup.find('b',text=name)
                if elt is not None:
                    for text in [u'פורטל הוועדה',u'מידע כללי']:
                        self._debug('trying to find element with text = '+text)
                        parent_tr=elt.findParent('tr')
                        if parent_tr is not None:
                            next_tr=parent_tr.findNext('tr')
                            if next_tr is not None:
                                a=next_tr.find('a',text=text)
                                if a is not None:
                                    if a.parent is not None:
                                        if a.parent.has_key('href'):
                                            href=a.parent['href']
                                        else: self._debug('href not in a.parent - '+str(a.parent))
                                    else: self._debug('a.parent is None')
                                else: self._debug('failed to find a')
                                if len(href)>2: break
                                else: self._debug('href is less then 2 characters: '+href)
                            else: self._debug('failed to find next_tr')
                        else: self._debug('failed to find parent_tr')
                else: self._debug('failed to find b element')
                if len(href)>2: break
            if len(href)>2:
                if href[0]=='/':
                    href=self.KNESSET_BASEHREF+href
                elif href[0:4]!='http':
                    href=self.KNESSET_BASEHREFPATH+href
                return [self._get_committee_mainpage_soup(href),href]
            else:
                return ret
        except Exception, e:
            self._warn('failed to fetch committee mainpage, exception = '+str(e))
            traceback.print_exc(file=sys.stdout)
            return ret
        
    def _get_committee_mainpage_soup(self,href):
        return BeautifulSoup(urllib.urlopen(href).read())
              
    def _update_committee_broadcasts_url(self,comm):
        try:
            url=''
            index=self._get_committees_index_page()
            soup=BeautifulSoup(index)
            self._debug('fetching committee main page')
            [main,mainpage_href]=self._get_committee_mainpage(soup,comm.name)
            if type(main).__name__=='BeautifulSoup':
                self._debug('trying to find link for braodcasts url in the committee main page')
                vaadot_meshudarot=u'ועדות משודרות'
                elt=main('a',text=vaadot_meshudarot)
                if len(elt)>0:
                    try:
                        path=elt[0].parent['href']
                        url=self.PORTAL_KNESSET_BASEHREF+path
                        self._debug('got url from vaadot meshudarot tag')
                    except Exception, e:
                        pass
                if len(url)==0:
                    self._debug('failed to find vaadot meshudarot tag')
                    self._debug('trying search history tag')
                    text=u'חיפוש בהיסטורית ועדות משודרות'
                    elt=main('B',text=text)
                    if len(elt)>0:
                        elt=elt[0].parent
                        try:
                            url=elt['href']
                        except Exception:
                            try:
                                url=elt.parent['href']
                            except Exception: pass
                        if len(url)>0:
                            self._debug('get url from search history tag')
                            url=self.KNESSET_BASEHREF+url
                if len(url)==0:
                    self._debug('failed to find search history tag')
                    self._debug('trying alternative vaadot meshudarot link')
                    elt=main('span',text=vaadot_meshudarot)
                    if len(elt)>0:
                        try:
                            url=elt[0].parent.parent['href']
                        except Exception, e:
                            url=''
                        if len(url)>0:
                            url=mainpage_href+'/'+url
            else: self._debug('failed to fetch committee main page')
            if len(url)>6:
                self._update_committee_portal_knesset_broadcasts_url(comm,url)
            return url
        except Exception, e:
            self._warn('exception while trying to get broadcasts url from committee mainpage')
            self._warn('exception = '+str(e))
            traceback.print_exc(file=sys.stdout)
            return ''
    
    def _update_committee_portal_knesset_broadcasts_url(self,comm,url):
        comm.portal_knesset_broadcasts_url=url
        comm.save()
    
    def _get_committee_videos_soup(self,bcasturl):
        return BeautifulSoup(urllib.urlopen(bcasturl).read())
    
    def _get_committee_videos(self,bcasturl):
        videos=[]
        mmsurls=[]
        try:
            soup=self._get_committee_videos_soup(bcasturl)
            elts=soup('span',{'onclick':re.compile(".*asf.*")})
            if len(elts)>0:
                for elt in elts:
                    onclick=elt['onclick']
                    r=re.compile("SetPlayerFileName\\('(.*),([0-9]*)/([0-9]*)/([0-9]*) ([0-9]*):([0-9]*):([0-9]*) (.*)'\\);",re.DOTALL)
                    mtch=re.search(r,onclick)
                    if mtch is not None:
                        groups=mtch.groups()
                        if len(groups)==8:
                            mmsurl=groups[0]
                            if mmsurl not in mmsurls:
                                title=groups[7]
                                # try to get a better title
                                while elt.nextSibling is not None:
                                    elt=elt.nextSibling
                                    if len(elt.string)>len(title):
                                        title=elt.string
                                        break
                                title=re.sub('^[0-9]*\. ', '', title)
                                title=re.sub("\n", '', title)
                                title=re.sub("``", "'", title)
                                title=title.strip()
                                mmsurls.append(mmsurl)
                                videos.append({
                                    'mmsurl':mmsurl,
                                    'title':title,
                                    'datetime':datetime.datetime(int(groups[3]),int(groups[2]),int(groups[1]),int(groups[4]),int(groups[5]),int(groups[6])),
                                })
                    else: self._debug('mtch is None for '+onclick)
            if len(videos)==0:
                elts=soup('a',{'href':re.compile(".*asf.*")})
                for elt in elts:
                    href=elt['href']
                    r=re.compile("SetPlayerFileName\\('(.*)','(.*)'\\)")
                    mtch=re.search(r,href)
                    groups=mtch.groups()
                    if len(groups)==2:
                        videos.append({
                            'mmsurl':groups[0],
                            'title':groups[1],
                            'datetime':datetime.datetime.now()
                        })
            return videos
        except Exception, e:
            self._warn('exception while trying to get videos from broadcasts url')
            self._warn('bcasturl = '+str(bcasturl))
            self._warn('exception = '+str(e))
            traceback.print_exc(file=sys.stdout)
            return videos
    
    def _get_committee_num_mms_videos(self,comm,group,ignoreHide,embed_link):
        return get_videos_queryset(comm,group=group,ignoreHide=ignoreHide).filter(embed_link=embed_link).count()
    
    def _getMmsVideoFields(self,video,comm):
        return {
            'embed_link':video['mmsurl'],
            'title':video['title'],
            'source_type':'mms-knesset-portal',
            'published':video['datetime'],
            'group':'mms',
            'content_object':comm
        }
        
    def _saveVideo(self,videoFields):
        v=Video(**videoFields)
        v.save()
    
    def _update_committee_mms_video(self,comm,video):
        numcurvids=self._get_committee_num_mms_videos(comm, 'mms', True, video['mmsurl'])
        if numcurvids==0:
            self._saveVideo(self._getMmsVideoFields(video, comm))
            self._debug('saved video - '+video['mmsurl'])
        else:
            self._debug('video already exists - '+video['mmsurl'])
