# encoding: utf-8

import urllib,urllib2,re,datetime,traceback,sys,os,subprocess
from BeautifulSoup import BeautifulSoup
from django.conf import settings
from committees.models import Committee, CommitteeMeeting

URL="http://www.knesset.gov.il/plenum/heb/plenum_queue.aspx"
ROBOTS_URL="http://www.knesset.gov.il/robots.txt"
FULL_URL="http://www.knesset.gov.il/plenum/heb/display_full.asp"
FILE_BASE_URL="http://www.knesset.gov.il/plenum/heb/"
WORDS_OF_THE_KNESSET=u"דברי הכנסת"
WORDS_OF_THE_KNESSET_FULL=u"כל הפרוטוקול"
DISCUSSIONS_ON_DATE=u"הדיונים בתאריך"

verbosity=1

def _debug(str):
    global verbosity
    if verbosity>1: print str

def _get_committees_index_page(full):
    if full:
        url=FULL_URL
        encoding='iso_8859_8'
    else:
        url=URL
        encoding='utf8'
    _debug('getting the html from '+url)
    try:
        return unicode(urllib2.urlopen(url).read(),encoding)
    except Exception, e:
        print 'could not fetch committees_index_page, exception: '+str(e)
        traceback.print_exc(file=sys.stdout)

def _copy(url,to):
    #_debug("copying from "+url+" to "+to)
    d=os.path.dirname(to)
    if not os.path.exists(d):
        os.makedirs(d)
    if not os.path.exists(to):
        urllib.urlretrieve(url,to+".tmp")
        os.rename(to+'.tmp',to)
    else:
        _debug('already downloaded')

def _antiword(filename):
    cmd='antiword -x db '+filename+' > '+filename+'.awdb.xml'
    #_debug(cmd)
    subprocess.call(cmd,shell=True)
    xmldata=''
    with open(filename+'.awdb.xml','r') as f:
        xmldata=f.read()
    os.remove(filename+'.awdb.xml')
    return xmldata

def _urlAlreadyDownloaded(url):
    plenum=Committee.objects.filter(type='plenum')[0]
    if CommitteeMeeting.objects.filter(committee=plenum,src_url=url).count()>0:
        return True
    else:
        return False

def _updateDb(xmlData,url,year,mon,day):
    plenum=Committee.objects.filter(type='plenum')[0]
    cms=CommitteeMeeting.objects.filter(committee=plenum,src_url=url)
    if cms.count()>0:
        meeting=cms[0]
    else:
        meeting=CommitteeMeeting(
            committee=plenum,
            date=datetime.datetime(int(year),int(mon),int(day)),
            src_url=url,
            topics=u'ישיבת מליאה מתאריך '+day+'/'+mon+'/'+year,
            date_string=''+day+'/'+mon+'/'+year
        )
    meeting.protocol_text=xmlData
    meeting.save()

def _downloadLatest(full,redownload):
    html=_get_committees_index_page(full)
    soup=BeautifulSoup(html)
    if full:
        words_of_the_knesset=WORDS_OF_THE_KNESSET_FULL
    else:
        words_of_the_knesset=WORDS_OF_THE_KNESSET
    aelts=soup('a',text=words_of_the_knesset)
    for aelt in aelts:
        selt=aelt.findPrevious('span',text=re.compile(DISCUSSIONS_ON_DATE))
        url=FILE_BASE_URL+aelt.parent.get('href')
        filename=re.search(r"[^/]*$",url).group()
        _debug(filename)
        m=re.search(r"\((.*)/(.*)/(.*)\)",selt)
        if m is None:
            selt=selt.findNext()
            m=re.search(r"\((.*)/(.*)/(.*)\)",unicode(selt))
        if m is not None:
            day=m.group(1)
            mon=m.group(2)
            year=m.group(3)
            url=url.replace('/heb/..','')
            _debug(url)
            if not redownload and _urlAlreadyDownloaded(url):
                _debug('url already downloaded')
            else:
                DATA_ROOT = getattr(settings, 'DATA_ROOT')
                _copy(url.replace('/heb/..',''),DATA_ROOT+'plenum_protocols/'+year+'_'+mon+'_'+day+'_'+filename)
                xmlData=_antiword(DATA_ROOT+'plenum_protocols/'+year+'_'+mon+'_'+day+'_'+filename)
                os.remove(DATA_ROOT+'plenum_protocols/'+year+'_'+mon+'_'+day+'_'+filename)
                _updateDb(xmlData,url,year,mon,day)
                

def Download(verbosity_level,redownload):
    global verbosity
    verbosity=int(verbosity_level)
    _downloadLatest(False,redownload)
    _downloadLatest(True,redownload)

