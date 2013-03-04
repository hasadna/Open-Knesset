# encoding: utf-8

from django.core.management.base import NoArgsCommand
from optparse import make_option
import urllib,urllib2,re,datetime,traceback,sys,os,subprocess
from BeautifulSoup import BeautifulSoup
from dateutil import zoneinfo
from committees.models import Committee
from events.models import Event
from django.contrib.contenttypes.models import ContentType

URL='http://main.knesset.gov.il/Activity/plenum/Pages/GeneralAgenda.aspx'

committee_ct=ContentType.objects.get_for_model(Committee)

verbosity=1

def _debug(str):
    global verbosity
    if verbosity>1: print str

def _downloadHtml():
    _debug('downloading from '+URL)
    return unicode(urllib2.urlopen(URL).read(),'utf8')

def _parseHtml(html):
    _debug('parsing the downloaded html (length='+str(len(html))+')')
    elts=re.findall(re.compile(u"([0-9]+)/([0-9]+)/([0-9]+)[\s\S]בשעה[\s\S]([0-9]+):([0-9]+)"),html)
    ans=[]
    for elt in elts:
        ans.append(
            datetime.datetime(
                year=int(elt[2]), month=int(elt[1]), day=int(elt[0]),
                hour=int(elt[3]), minute=int(elt[4]), second=0
            )
        )
    _debug(ans)
    return ans

def _updateEvent(committee,date):
    _debug('updating event: '+str(date))
    ev, created = Event.objects.get_or_create(
        when = date,
        #when_over = when_over,
        #when_over_guessed = p.end_guessed,
        where = unicode(committee),
        what = u'מליאת הכנסת',
        which_pk = committee.id,
        which_type = committee_ct,
    )
    if created:
        _debug('added a new event')
    else:
        _debug('event already exists')

class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        global verbosity
        verbosity=options.get('verbosity',1)
        html=_downloadHtml()
        dates=_parseHtml(html)
        committee=Committee.objects.get(type='plenum')
        for date in dates:
            _updateEvent(committee,date)      
            
            
            