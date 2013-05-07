# -*- coding: utf-8 -*-
import urllib2, urllib, cookielib, re, gzip, datetime, time, logging, os, sys,traceback, difflib

from cStringIO import StringIO
from pyth.plugins.rtf15.reader import Rtf15Reader
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max,Count

from mks.models import Member,Party,Membership,WeeklyPresence
from persons.models import Person,PersonAlias
from laws.models import (Vote, VoteAction, Bill, Law, PrivateProposal,
     KnessetProposal, GovProposal, GovLegislationCommitteeDecision)
from links.models import Link
from committees.models import Committee,CommitteeMeeting
from knesset.utils import cannonize

import mk_info_html_parser as mk_parser
import parse_presence, parse_laws, mk_roles_parser, parse_remote

from parse_gov_legislation_comm import ParseGLC

from syncdata_globals import p_explanation,strong_explanation,explanation

ENCODING = 'utf8'

DATA_ROOT = getattr(settings, 'DATA_ROOT',
                    os.path.join(settings.PROJECT_ROOT, os.path.pardir, os.path.pardir, 'data'))

logger = logging.getLogger("open-knesset.syncdata")

try:
    SPECIAL_COMMITTEES = map(lambda x: dict(name=x, commitee=Committee.objects.get(name=x)),
                         [u"הוועדה המשותפת לנושא סביבה ובריאות",])
except:
    logger.warn("can't find special committees")
    SPECIAL_COMMITTEES = {}

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--all', action='store_true', dest='all',
            help="runs all the syncdata sub processes (like --download --load --process --dump)"),
        make_option('--download', action='store_true', dest='download',
            help="download data from knesset website to local files."),
        make_option('--load', action='store_true', dest='load',
            help="load the data from local files to the db."),
        make_option('--process', action='store_true', dest='process',
            help="run post loading process."),
        make_option('--dump', action='store_true', dest='dump-to-file',
            help="write votes to tsv files (mainly for debug, or for research team)."),
        make_option('--laws', action='store_true', dest='laws',
            help="download and parse laws"),
        make_option('--update', action='store_true', dest='update',
            help="online update of data."),
        make_option('--committees', action='store_true', dest='committees',
            help="online update of committees data."),

    )
    help = "Downloads data from sources, parses it and loads it to the Django DB."

    requires_model_validation = False

    last_downloaded_vote_id = 0
    last_downloaded_member_id = 0

    def read_laws_page(self,index):
        url = 'http://www.knesset.gov.il/privatelaw/plaw_display.asp?LawTp=2'
        data = urllib.urlencode({'RowStart':index})
        urlData = urllib2.urlopen(url,data)
        page = urlData.read().decode('windows-1255').encode('utf-8')
        return page

    def parse_laws_page(self,page):
        names = []
        exps = []
        links = []
        count = -1
        lines = page.split('\n')
        for line in lines:
            #print line
            r = re.search("""Href=\"(.*?)\">""",line)
            if r != None:
                link = 'http://www.knesset.gov.il/privatelaw/' + r.group(1)
            r = re.search("""<td class="LawText1">(.*)""",line)
            if r != None:
                name = r.group(1).replace("</td>","").strip()
                if len(name)>1 and name.find('span')<0:
                    names.append(name)
                    links.append(link)
                    exps.append('')
                    count += 1
            if re.search("""arrResume\[\d*\]""",line) != None:
                r = re.search('"(.*)"',line)
                if r != None:
                    try:
                        exps[count] += r.group(1).replace('\t',' ')
                    except:
                        pass

        return (names,exps,links)

    def get_laws_data(self):
        f = gzip.open(os.path.join(DATA_ROOT, 'laws.tsv.gz'), "wb")
        for x in range(0,910,26): # TODO: find limits of download
        #for x in range(0,50,26): # for debug
            page = self.read_laws_page(x)
            (names,exps,links) = self.parse_laws_page(page)
            for (name,exp,link) in zip(names,exps,links):
                f.write("%s\t%s\t%s\n" % (name,exp,link))
        f.close()

    def download_laws(self):
        """ returns an array of laws data: laws[i][0] - name, laws[i][1] - name for search, laws[i][2] - summary, laws[i][3] - link """
        laws = []
        for x in range(0,79,26): # read 4 last laws pages
            page = self.read_laws_page(x)
            (names,exps,links) = self.parse_laws_page(page)
            for (name,exp,link) in zip(names,exps,links):
                name_for_search = self.get_search_string(name)
                laws.append((name,name_for_search,exp,link))
        return laws

    def update_laws_data(self):
        logger.info("update laws data")
        laws = self.download_laws()
        logger.debug("finished downloading laws data")
        votes = Vote.objects.all().order_by('-time')[:200]
        for v in votes:
            search_name = self.get_search_string(v.title.encode('UTF-8'))
            for l in laws:
                if search_name.find(l[1]) >= 0:
                    #print "match"
                    v.summary = l[2]
                    v.save()
                    try:
                        (link, created) = Link.objects.get_or_create(title=u'מסמך הצעת החוק באתר הכנסת', url=l[3], content_type=ContentType.objects.get_for_model(v), object_pk=str(v.id))
                        if created:
                            link.save()
                    except Exception, e:
                        logger.error(e)

            if v.full_text == None:
                self.get_full_text(v)
        logger.debug("finished updating laws data")

    def update_vote_from_page(self, vote_id, vote_src_url, page):
        (vote_label, vote_meeting_num, vote_num, date) = self.get_vote_data(page)
        logger.debug("downloaded data with vote id %d" % vote_id)
        vote_time_string = date.replace('&nbsp;',' ')
        for i in self.heb_months:
            if i in vote_time_string:
                month = self.heb_months.index(i)+1
        day = re.search("""(\d\d?)""", vote_time_string).group(1)
        year = re.search("""(\d\d\d\d)""", vote_time_string).group(1)
        vote_hm = datetime.datetime.strptime ( vote_time_string.split(' ')[-1], "%H:%M" )
        vote_time = datetime.datetime(int(year), int(month), int(day), vote_hm.hour, vote_hm.minute)
        #vote_label_for_search = self.get_search_string(vote_label)

        try:
            v = Vote.objects.get(src_id=vote_id)
            created = False
        except:
            v = Vote(title=vote_label, time_string=vote_time_string, importance=1, src_id=vote_id, time=vote_time)
            try:
                vote_meeting_num = int(vote_meeting_num)
                v.meeting_number = vote_meeting_num
            except:
                pass
            try:
                vote_num = int(vote_num)
                v.vote_number = vote_num
            except:
                pass
            v.src_url = vote_src_url
            v.save()
            if v.full_text_url != None:
                l = Link(title=u'מסמך הצעת החוק באתר הכנסת', url=v.full_text_url, content_type=ContentType.objects.get_for_model(v), object_pk=str(v.id))
                l.save()

        results = self.read_member_votes(page, return_ids=True)
        for (voter_id,voter_party,vote) in results:
            #f.write("%d\t%s\t%s\t%s\n" % (id,voter,party,vote))

            # transform party names to canonical form
            if(voter_party in self.party_aliases):
                voter_party = self.party_aliases[voter_party]

            # get the member voting
            try:
                m = Member.objects.get(pk=int(voter_id))
            except:
                exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
                logger.error("%svoter_id = %s", ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)), str(voter_id))
                continue

            # add the current member's vote
            va,created = VoteAction.objects.get_or_create(vote = v, member = m, type = vote)
            if created:
                va.save()

        v.update_vote_properties()
        v = Vote.objects.get(src_id=vote_id)
        self.find_synced_protocol(v)


    def update_votes(self, start_from_id=None, force_download=False):
        """Update votes data online, without saving to files.
           start_from_id - to manually override the id from which we'll start looking.
           force_download - force downloading vote data, even if we have this
                            record. used to re-scan after MKs have been added.
        """
        logger.info("update votes")
        current_max_src_id = Vote.objects.aggregate(Max('src_id'))['src_id__max']
        if current_max_src_id == None: # the db contains no votes, meaning its empty
            print "DB is empty. --update can only be used to update, not for first time loading. \ntry --all, or get some data using initial_data.json\n"
            return
        vote_id = start_from_id or current_max_src_id+1 # first vote to look for is the max_src_id we have plus 1, if not manually set
        limit_src_id = current_max_src_id + 100 # look for next 100 votes. if results are found, this value will be incremented.
        while vote_id < limit_src_id:
            if not force_download and Vote.objects.filter(src_id=vote_id).count(): # we already have this vote
                logger.debug('skipping reading vote with src_id %d, because we already have it' % vote_id)
                vote_id = vote_id + 1
                limit_src_id = current_max_src_id + 100 # look for next 100 votes.
                continue # skip reading it again.
            (page, vote_src_url) = self.read_votes_page(vote_id)
            title = self.get_page_title(page)
            if(title == """הצבעות במליאה-חיפוש"""): # found no vote with this id
                logger.debug("no vote found at id %d" % vote_id)
            else:
                limit_src_id = vote_id + 100 # results found, so we'll look for at least 100 more votes
                self.update_vote_from_page(vote_id, vote_src_url, page)

            vote_id += 1

    def get_votes_data(self):
        self.update_last_downloaded_vote_id()
        r = range(self.last_downloaded_vote_id+1,17000) # this is the range of page ids to go over. currently its set manually.
        for id in r:
            f  = gzip.open(os.path.join(DATA_ROOT, 'results.tsv.gz'), "ab")
            f2 = gzip.open(os.path.join(DATA_ROOT, 'votes.tsv.gz'),"ab")
            (page, src_url) = self.read_votes_page(id)
            title = self.get_page_title(page)
            if(title == """הצבעות במליאה-חיפוש"""): # found no vote with this id
                logger.debug("no vote found at id %d" % id)
            else:
                count_for = 0
                count_against = 0
                count_abstain = 0
                count_no_vote = 0
                (name, meeting_num, vote_num, date) = self.get_vote_data(page)
                results = self.read_member_votes(page)
                for (voter,party,vote) in results:
                    f.write("%d\t%s\t%s\t%s\n" % (id,voter,party,vote))
                    if(vote=="for"):
                        count_for += 1
                    if(vote=="against"):
                        count_against += 1
                    if(vote=="abstain"):
                        count_abstain += 1
                    if(vote=="no-vote"):
                        count_no_vote += 1
                f2.write("%d\t%s\t%s\t%s\t%s\t%s\t%d\t%d\t%d\t%d\n" % (id, src_url, name, meeting_num, vote_num, date, count_for, count_against, count_abstain, count_no_vote))
                logger.debug("downloaded data with vote id %d" % id)
            #print " %.2f%% done" % ( (100.0*(float(id)-r[0]))/(r[-1]-r[0]) )
            f.close()
            f2.close()

    def update_last_downloaded_member_id(self):
        """
        Reads local members file, and sets self.last_downloaded_member_id to the highest id found in the file.
        This is later used to skip downloading of data alreay downloaded.
        """
        try:
            f = gzip.open(os.path.join(DATA_ROOT, 'members.tsv.gz'))
        except:
            self.last_downloaded_member_id = 0
            logger.debug("members file does not exist. setting last_downloaded_member_id to 0")
            return
        content = f.read().split('\n')
        for line in content:
            if(len(line)<2):
                continue
            s = line.split('\t')
            id = int(s[0])
            if id > self.last_downloaded_member_id:
                self.last_downloaded_member_id = id
        logger.debug("last member id found in local files is %d. " % self.last_downloaded_member_id)
        f.close()

    def get_members_data(self, max_mk_id=1000):
        """downloads members data to local files
        """
        # TODO - find max member id in knesset website and use for max_mk_id

        f  = gzip.open(os.path.join(DATA_ROOT, 'members.tsv.gz'), "wb")

        fields = ['img_link','טלפון','פקס','אתר נוסף',
                  'דואר אלקטרוני','מצב משפחתי',
                  'מספר ילדים','תאריך לידה','שנת לידה',
                  'מקום לידה','תאריך פטירה','שנת עלייה',
                  'כנסת 18', 'כנסת 19']
        # note that hebrew strings order is right-to-left
        # so output file order is id, name, img_link, phone, ...

        fields = [unicode(field.decode('utf8')) for field in fields]

        for id in range(1,max_mk_id):
            m = mk_parser.MKHtmlParser(id).Dict
            if (m.has_key('name') and m['name'] != None): name = m['name'].replace(u'\xa0',u' ').encode(ENCODING).replace('&nbsp;',' ')
            else: continue
            f.write("%d\t%s\t" % (id, name))
            for field in fields:
                value = ''
                if (m.has_key(field) and m[field]!=None):
                    value = m[field].encode(ENCODING)
                f.write("%s\t" % (  value ))
            f.write("\n")
        f.close()

    def download_all(self):
        self.get_members_data()
        self.get_votes_data()
        self.get_laws_data()


    def update_last_downloaded_vote_id(self):
        """
        Reads local votes file, and sets self.last_downloaded_id to the highest id found in the file.
        This is later used to skip downloading of data alreay downloaded.
        """
        try:
            f = gzip.open(os.path.join(DATA_ROOT, 'votes.tsv.gz'))
        except:
            self.last_downloaded_vote_id = 0
            logger.debug("votes file does not exist. setting last_downloaded_vote_id to 0")
            return
        content = f.read().split('\n')
        for line in content:
            if(len(line)<2):
                continue
            s = line.split('\t')
            vote_id = int(s[0])
            if vote_id > self.last_downloaded_vote_id:
                self.last_downloaded_vote_id = vote_id
        logger.debug("last id found in local files is %d. " % self.last_downloaded_vote_id)
        f.close()

    def update_mks_is_current(self):
        """Set is_current=True if and only if mk is currently serving.
           This is done by looking at the presence page in the knesset website.
        """
        URL = 'http://www.knesset.gov.il/presence/heb/PresentList.aspx'
        x = urllib2.urlopen(URL).read()
        m = re.search('lbHowManyMKs2(.*)lbHowManyMKs', x, re.DOTALL)
        mks = re.findall('mk_individual_id_t=(\d+)', m.group())
        logger.debug('found %d current mks' % len(mks))
        updated = Member.objects.filter(id__in=mks).update(is_current=True)
        logger.debug('updated %d mks to is_current=True' % updated)
        updated = Member.objects.exclude(id__in=mks).update(is_current=False)
        logger.debug('updated %d mks to is_current=False' % updated)

    def update_members_from_file(self):
        logger.debug('update_members_from_file')
        f = gzip.open(os.path.join(DATA_ROOT, 'members.tsv.gz'))
        content = f.read().split('\n')
        for line in content:
            if len(line) <= 1:
                continue
            (member_id, name, img_url, phone, fax, website, email,
             family_status, number_of_children, date_of_birth,
             year_of_birth, place_of_birth, date_of_death,
             year_of_aliyah, k18, k19, _) = line.split('\t')
            if email != '':
                email = email.split(':')[1]
            try:
                if date_of_birth.find(',')>=0:
                    date_of_birth = date_of_birth.split(',')[1].strip(' ')
                date_of_birth = datetime.datetime.strptime ( date_of_birth, "%d/%m/%Y" )
            except:
                date_of_birth = None
            try:
                if date_of_birth.find(',')>=0:
                    date_of_death = date_of_birth.split(',')[1].strip(' ')
                date_of_death = datetime.datetime.strptime ( date_of_death, "%d/%m/%Y" )
            except:
                date_of_death = None
            try: year_of_birth = int(year_of_birth)
            except: year_of_birth = None
            try: year_of_aliyah = int(year_of_aliyah)
            except: year_of_aliyah = None
            try: number_of_children = int(number_of_children)
            except: number_of_children = None

            try:
                m = Member.objects.get(id=member_id)
                m.phone = phone
                m.fax = fax
                m.email = email
                m.family_status = family_status
                m.number_of_children = number_of_children
                m.date_of_death = date_of_death
                m.save()
                logger.debug('updated member %d' % m.id)
            except Member.DoesNotExist: # member_id not found. create new
                m = Member(id=member_id, name=name, img_url=img_url, phone=phone, fax=fax, website=None, email=email, family_status=family_status,
                            number_of_children=number_of_children, date_of_birth=date_of_birth, place_of_birth=place_of_birth,
                            date_of_death=date_of_death, year_of_aliyah=year_of_aliyah)
                m.save()
                m = Member.objects.get(pk=member_id) # make sure we are are
                    # working on the db object. e.g m.id is a number.
                logger.debug('created member %d' % m.id)
                if len(website)>0:
                    l = Link(title='אתר האינטרנט של %s' % name, url=website, content_type=ContentType.objects.get_for_model(m), object_pk=str(m.id))
                    l.save()

            if k19: # KNESSET 19 specific
                parties = Party.objects.filter(knesset_id=19).values_list('name','id')
                k19 = k19.decode(ENCODING)
                for k,v in parties:
                    if k in k19:
                        m.current_party_id = int(v)
                        logger.debug('member %s, k19 %s, party %s'
                                     % (m.name,
                                        k19,
                                        k))
                        m.save()
                if m.current_party is None:
                    logger.debug('member %s, k19 %s not found' %
                                 (m.name,
                                  k19))

    def get_search_string(self,s):
        if isinstance(s,unicode):
            s = s.replace(u'\u201d','').replace(u'\u2013','')
        else:
            s = s.replace('\xe2\x80\x9d','').replace('\xe2\x80\x93','')
        return re.sub(r'["\(\) ,-]', '', s)

    heb_months = ['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר']


    # some party names appear in the knesset website in several forms.
    # this dictionary is used to transform them to canonical form.
    party_aliases = {'עבודה':'העבודה',
                    'ליכוד':'הליכוד',
                    'ש"ס-התאחדות ספרדים שומרי תורה':'ש"ס',
                    'יחד (ישראל חברתית דמוקרטית) והבחירה הדמוקרטית':'יחד (ישראל חברתית דמוקרטית) והבחירה הדמוקרטית',
                    'בל"ד-ברית לאומית דמוקרטית':'בל"ד',
                    'אחריות לאומית':'קדימה',
                    'יחד (ישראל חברתית דמוקרטית) והבחירה הדמוקרטית':'מרצ-יחד והבחירה הדמוקרטית',
                    'יחד והבחירה הדמוקרטית':'מרצ-יחד והבחירה הדמוקרטית',
                    'יחד והבחירה הדמוקרטית (מרצ לשעבר)':'מרצ-יחד והבחירה הדמוקרטית',
                    'יחד (ישראל חברתית דמוקרטית) והבחירה הדמוקרטית':'מרצ-יחד והבחירה הדמוקרטית',
                    'יחד  (ישראל חברתית דמוקרטית) והבחירה הדמוקרטית':'מרצ-יחד והבחירה הדמוקרטית',
                    }


    def update_db_from_files(self):
        logger.debug("Update DB From Files")

        try:
            laws = [] # of lists: [name,name_for_search,explanation,link]
            f = gzip.open(os.path.join(DATA_ROOT, 'laws.tsv.gz'))
            content = f.read().split('\n')
            for line in content:
                law = line.split('\t')
                if len(law)==3:
                    name_for_search = self.get_search_string(law[0])
                    law.insert(1, name_for_search)
                    laws.append(law)
            f.close()

            parties = dict() # key: party-name; value: Party
            members = dict() # key: member-name; value: Member
            votes   = dict() # key: id; value: Vote
            memberships = dict() # key: (member.id,party.id)
            current_max_src_id = Vote.objects.aggregate(Max('src_id'))['src_id__max']
            if current_max_src_id == None: # the db contains no votes, meaning its empty
                current_max_src_id = 0

            logger.debug("processing votes data")
            f = gzip.open(os.path.join(DATA_ROOT, 'votes.tsv.gz'))
            content = f.read().split('\n')
            for line in content:
                if len(line) <= 1:
                    continue
                (vote_id, vote_src_url, vote_label, vote_meeting_num, vote_num, vote_time_string, _, _, _, _) = line.split('\t')
                #if vote_id < current_max_src_id: # skip votes already parsed.
                #    continue
                vote_time_string = vote_time_string.replace('&nbsp;',' ')
                for i in self.heb_months:
                    if i in vote_time_string:
                        month = self.heb_months.index(i)+1
                day = re.search("""(\d\d?)""", vote_time_string).group(1)
                year = re.search("""(\d\d\d\d)""", vote_time_string).group(1)
                vote_hm = datetime.datetime.strptime ( vote_time_string.split(' ')[-1], "%H:%M" )
                vote_date = datetime.date(int(year),int(month),int(day))
                vote_time = datetime.datetime(int(year), int(month), int(day), vote_hm.hour, vote_hm.minute)
                vote_label_for_search = self.get_search_string(vote_label)

                #if vote_date < datetime.date(2009, 02, 24): # vote before 18th knesset
                #    continue

                try:
                    v = Vote.objects.get(src_id=vote_id)
                    created = False
                except:
                    v = Vote(title=vote_label, time_string=vote_time_string, importance=1, src_id=vote_id, time=vote_time)
                    try:
                        vote_meeting_num = int(vote_meeting_num)
                        v.meeting_number = vote_meeting_num
                    except:
                        pass
                    try:
                        vote_num = int(vote_num)
                        v.vote_number = vote_num
                    except:
                        pass
                    v.src_url = vote_src_url
                    for law in laws:
                        (_,law_name_for_search,law_exp,law_link) = law
                        if vote_label_for_search.find(law_name_for_search) >= 0:
                            v.summary = law_exp
                            v.full_text_url = law_link
                    v.save()
                    if v.full_text_url != None:
                        l = Link(title=u'מסמך הצעת החוק באתר הכנסת', url=v.full_text_url, content_type=ContentType.objects.get_for_model(v), object_pk=str(v.id))
                        l.save()
                votes[int(vote_id)] = v
            f.close()

            logger.debug("processing member votes data")
            f = gzip.open(os.path.join(DATA_ROOT, 'results.tsv.gz'))
            content = f.read().split('\n')
            for line in content:
                if(len(line)<2):
                    continue
                s = line.split('\t') # (id,voter,party,vote)

                vote_id = int(s[0])
                voter = s[1]
                voter_party = s[2]

                # transform party names to canonical form
                if(voter_party in self.party_aliases):
                    voter_party = self.party_aliases[voter_party]

                vote = s[3]

                try:
                    v = votes[vote_id]
                except KeyError: #this vote was skipped in this read, also skip voteactions and members
                    continue
                vote_date = v.time.date()

                # create/get the party appearing in this vote
                if voter_party in parties:
                    p = parties[voter_party]
                    created = False
                else:
                    p,created = Party.objects.get_or_create(name=voter_party)
                    parties[voter_party] = p
                #if created: # this is magic needed because of unicode chars. if you don't do this, the object p will have gibrish as its name.
                            #only when it comes back from the db it has valid unicode chars.
                #    p = Party.objects.get(name=voter_party)

                # use this vote's time to update the party's start date and end date
                if (p.start_date is None) or (p.start_date > vote_date):
                    p.start_date = vote_date
                if (p.end_date is None) or (p.end_date < vote_date):
                    p.end_date = vote_date
                if created: # save on first time, so it would have an id, be able to link, etc. all other updates are saved in the end
                    p.save()

                # create/get the member voting
                if voter in members:
                    m = members[voter]
                    created = False
                else:
                    try:
                        m = Member.objects.get(name=voter)
                    except:   # if there are several people with same age,
                        m = Member.objects.filter(name=voter).order_by('-date_of_birth')[0] # choose the younger. TODO: fix this
                    members[voter] = m
                #m.party = p;
                #if created: # again, unicode magic
                #    m = Member.objects.get(name=voter)
                # use this vote's date to update the member's dates.
                if (m.start_date is None) or (m.start_date > vote_date):
                    m.start_date = vote_date
                if (m.end_date is None) or (m.end_date < vote_date):
                    m.end_date = vote_date
                #if created: # save on first time, so it would have an id, be able to link, etc. all other updates are saved in the end
                #    m.save()


                # create/get the membership (connection between member and party)
                if ((m.id,p.id) in memberships):
                    ms = memberships[(m.id,p.id)]
                    created = False
                else:
                    ms,created = Membership.objects.get_or_create(member=m,party=p)
                    memberships[(m.id,p.id)] = ms
                #if created: # again, unicode magic
                #    ms = Membership.objects.get(member=m,party=p)
                # again, update the dates on the membership
                if (ms.start_date is None) or (ms.start_date > vote_date):
                    ms.start_date = vote_date
                if (ms.end_date is None) or (ms.end_date < vote_date):
                    ms.end_date = vote_date
                if created: # save on first time, so it would have an id, be able to link, etc. all other updates are saved in the end
                    ms.save()

                # add the current member's vote

                va,created = VoteAction.objects.get_or_create(vote = v, member = m, type = vote)
                if created:
                    va.save()

            logger.debug("done")
            logger.debug("saving data: %d parties, %d members, %d memberships " % (len(parties), len(members), len(memberships) ))
            for p in parties:
                parties[p].save()
            for m in members:
                members[m].save()
            #Member.objects.filter(end_date__isnull=True).delete() # remove members that haven't voted at all - no end date
            for ms in memberships:
                memberships[ms].save()
            #for va in voteactions:
            #    voteactions[va].save()
            logger.debug("done")
            f.close()
        except:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            logger.error("%s", ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)))


    def calculate_votes_importances(self):
        """
        Calculates votes importances. currently uses rule of thumb: number of voters against + number of voters for / 120.
        """
        for v in Vote.objects.all():
            v.importance = float(v.votes.filter(voteaction__type='for').count() + v.votes.filter(voteaction__type='against').count()) / 120
            v.save()

    def read_votes_page(self,voteId, retry=0):
        """
        Gets a votes page from the knesset website.
        returns a string (utf encoded)
        """
        url = "http://www.knesset.gov.il/vote/heb/Vote_Res_Map.asp?vote_id_t=%d" % voteId
        try:
            urlData = urllib2.urlopen(url)
            page = urlData.read().decode('windows-1255').encode('utf-8')
            time.sleep(2)
        except Exception,e:
            logger.warn(e)
            if retry < 5:
                logger.warn("waiting some time and trying again... (# of retries = %d)" % (retry+1) )
                page = self.read_votes_page(voteId, retry+1)
            else:
                logger.error("failed too many times. last error: %s", e)
                return None
        return (page, url)

    def read_member_votes(self,page,return_ids=False):
        """
        Returns a tuple of (name, party, vote) describing the vote found in page, where:
         name is a member name
         party is the member's party
         vote is 'for','against','abstain' or 'no-vote'
         if return_ids = True, it will return member id, and not name as first element.
        """
        results = []
        pattern = re.compile("""Vote_Bord""")
        match = pattern.split(page)
        last_party = None
        for i in match:
            vote = ""
            if(re.match("""_R1""", i)):
                vote = "for"
            if(re.match("""_R2""", i)):
                vote = "against"
            if(re.match("""_R3""", i)):
                vote = "abstain"
            if(re.match("""_R4""", i)):
                vote = "no-vote"
            if(vote != ""):
                name = re.search("""DataText4>([^<]*)</a>""",i).group(1);
                name = re.sub("""&nbsp;""", " ", name)
                m_id = re.search("""mk_individual_id_t=(\d+)""",i).group(1)
                party = re.search("""DataText4>([^<]*)</td>""",i).group(1);
                party = re.sub("""&nbsp;""", " ", party)
                if(party == """ " """):
                    party = last_party
                else:
                    last_party = party
                if return_ids:
                    results.append((m_id, party, vote))
                else:
                    results.append((name, party, vote))

        return results


    def get_page_title(self,page):
        """
        Returns the title of a vote page
        """
        title = re.search("""<TITLE>([^<]*)</TITLE>""", page)
        return title.group(1)

    def get_vote_data(self,page):
        """
        Returns name, meeting number, vote number and date from a vote page
        """
        meeting_num = re.search("""מספר ישיבה: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        vote_num = re.search("""מספר הצבעה: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        name = re.search("""שם החוק: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        name = name.replace("\t"," ")
        name = name.replace("\n"," ")
        name = name.replace("\r"," ")
        name = name.replace("&nbsp;"," ")
        date = re.search("""תאריך: </td>[^<]*<[^>]*>([^<]*)<""",page).group(1)
        return (name, meeting_num, vote_num, date)


    def find_synced_protocol(self, v):
        try:
            search_text = ''
            url = "http://online.knesset.gov.il/eprotocol/PUBLIC/SearchPEOnline.aspx"
            to_day = from_day = str(v.time.day)
            to_month = from_month = str(v.time.month)
            to_year = from_year = str(v.time.year)
            m = re.search(' - (.*),?', v.title)
            if not m:
                logger.debug("couldn't create search string for vote\nvote.id=%s\nvote.title=%s\n", str(v.id), v.title)
                return
            search_text = urllib2.quote(m.group(1).replace('(','').replace(')','').replace('`','').encode('utf8'))

            # I'm really sorry for the next line, but I really had no choice:
            params = '__EVENTARGUMENT=&__EVENTTARGET=&__LASTFOCUS=&__PREVIOUSPAGE=bEfxzzDx0cPgMul_87gMIa3L4OOi0E21r4EnHaLHKQAsWXdde-10pzxRGZZaJFCK0&__SCROLLPOSITIONX=0&__SCROLLPOSITIONY=0&__VIEWSTATE=%2FwEPDwUKMjA3MTAzNTc1NA8WCB4VU0VTU0lPTl9SQU5ET01fTlVNQkVSAswEHhFPTkxZX0RBVEVTX1NFQVJDSGgeEFBSRVZJRVdfRFRfQ0FDSEUy5AQAAQAAAP%2F%2F%2F%2F8BAAAAAAAAAAQBAAAA7AFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5EaWN0aW9uYXJ5YDJbW1N5c3RlbS5JbnQzMiwgbXNjb3JsaWIsIFZlcnNpb249Mi4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XSxbU3lzdGVtLkRhdGEuRGF0YVRhYmxlLCBTeXN0ZW0uRGF0YSwgVmVyc2lvbj0yLjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODldXQMAAAAHVmVyc2lvbghDb21wYXJlcghIYXNoU2l6ZQADAAiRAVN5c3RlbS5Db2xsZWN0aW9ucy5HZW5lcmljLkdlbmVyaWNFcXVhbGl0eUNvbXBhcmVyYDFbW1N5c3RlbS5JbnQzMiwgbXNjb3JsaWIsIFZlcnNpb249Mi4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0IAAAAAAkCAAAAAAAAAAQCAAAAkQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5HZW5lcmljRXF1YWxpdHlDb21wYXJlcmAxW1tTeXN0ZW0uSW50MzIsIG1zY29ybGliLCBWZXJzaW9uPTIuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV1dAAAAAAseFEFQUFJOQ19DT1VOVEVSX0NBQ0hFMtgEAAEAAAD%2F%2F%2F%2F%2FAQAAAAAAAAAEAQAAAOABU3lzdGVtLkNvbGxlY3Rpb25zLkdlbmVyaWMuRGljdGlvbmFyeWAyW1tTeXN0ZW0uSW50MzIsIG1zY29ybGliLCBWZXJzaW9uPTIuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV0sW1N5c3RlbS5JbnQzMiwgbXNjb3JsaWIsIFZlcnNpb249Mi4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0DAAAAB1ZlcnNpb24IQ29tcGFyZXIISGFzaFNpemUAAwAIkQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5HZW5lcmljRXF1YWxpdHlDb21wYXJlcmAxW1tTeXN0ZW0uSW50MzIsIG1zY29ybGliLCBWZXJzaW9uPTIuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV1dCAAAAAAJAgAAAAAAAAAEAgAAAJEBU3lzdGVtLkNvbGxlY3Rpb25zLkdlbmVyaWMuR2VuZXJpY0VxdWFsaXR5Q29tcGFyZXJgMVtbU3lzdGVtLkludDMyLCBtc2NvcmxpYiwgVmVyc2lvbj0yLjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODldXQAAAAALFgJmD2QWAgIDD2QWAgIDD2QWCgIDDw8WAh4EVGV4dAX%2BBiBTRUxFQ1QgICAgIHRNZXRhRGF0YS5pSXRlbUlELCB0TWV0YURhdGEuaVRvcklELCB0TWV0YURhdGEuaUl0ZW1UeXBlLCB0TWV0YURhdGEuaVBhcmVudCwgdE1ldGFEYXRhLmlJdGVtUmF3SWQsIHRNZXRhRGF0YS5zVGl0bGUsICAgICAgICAgICAgICB0TWV0YURhdGEuc1RleHQsIHRNZXRhRGF0YS5pUGFnZSwgIHRNZXRhRGF0YS5pV29yZENvdW50ZXIsIHRNZXRhRGF0YS5pQnVsa051bSwgdE1ldGFEYXRhLmlFbGVtZW50SW5lZHhlciAgRlJPTSAgICAgICB0RGlzY3Vzc2lvbnMgSU5ORVIgSk9JTiAgICAgICAgICAgICB0VG9yaW0gT04gdERpc2N1c3Npb25zLmlEaXNjSUQgPSB0VG9yaW0uaURpc2NJRCBJTk5FUiBKT0lOICAgICAgICAgICAgIHRNZXRhRGF0YSBPTiB0VG9yaW0uaVRvciA9IHRNZXRhRGF0YS5pVG9ySUQgIFdIRVJFICB0VG9yaW0uYkhhc0ZpbmFsRG9jPTAgQU5EICAoQ09OVEFJTlMoc1RleHQsIE4nIteQ15nXqdeV16gg15TXl9eV16cg15TXptei16og15fXldenINeT15XXkyDXkdefINeS15XXqNeZ15XXnyDXqteZ16fXldefINeU16rXqSIi16IgMjAxMCIgICcpIE9SIENPTlRBSU5TKHNUaXRsZSwgTici15DXmdep15XXqCDXlNeX15XXpyDXlNem16LXqiDXl9eV16cg15PXldeTINeR158g15LXldeo15nXldefINeq15nXp9eV158g15TXqtepIiLXoiAyMDEwIiAgJykpIEFORCAgREFURURJRkYoREFZLCAnMi8yMi8yMDEwJyAsIHREaXNjdXNzaW9ucy5kRGF0ZSk%2BPTAgQU5EICBEQVRFRElGRihEQVksIHREaXNjdXNzaW9ucy5kRGF0ZSwgJzIvMjIvMjAxMCcpPj0wIEFORCAgdERpc2N1c3Npb25zLmlLbmVzc2V0IElOICgxOCkgQU5EICB0RGlzY3Vzc2lvbnMuaURpc2NUeXBlID0gMSBPUkRFUiBCWSBbaVRvcklEXSBERVNDLCBbaUVsZW1lbnRJbmVkeGVyXWRkAgUPDxYCHwRlZGQCBw9kFhYCAQ8PFgIfBAUi15fXmdek15XXqSDXkSLXk9eR16jXmSDXlNeb16DXodeqImRkAgMPD2QWAh4Jb25rZXlkb3duBcgBaWYgKChldmVudC53aGljaCAmJiBldmVudC53aGljaCA9PSAxMykgfHwgKGV2ZW50LmtleUNvZGUgJiYgZXZlbnQua2V5Q29kZSA9PSAxMykpICAgICB7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfYnRuU2VhcmNoJykuY2xpY2soKTtyZXR1cm4gZmFsc2U7fSAgICAgZWxzZSByZXR1cm4gdHJ1ZTtkAgcPDxYCHhRDdHJsRm9jdXNBZnRlclNlbGVjdAUpY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9idG5TZWFyY2hkFgQCAw8PZBYEHgZvbmJsdXIFSEhpZGVBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaERvdmVyX3dzQXV0b0NvbXBsZXRlMR4Hb25rZXl1cAVbcmV0dXJuIEF1dG9Db21wbGV0ZUNoZWNrRGVsZXRlKGV2ZW50LCAnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRG92ZXJfaGRuVmFsdWUnKWQCBQ8WBh4RT25DbGllbnRQb3B1bGF0ZWQFVkF1dG9Db21wbGV0ZV9DbGllbnRQb3B1bGF0ZWRfY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRG92ZXJfd3NBdXRvQ29tcGxldGUxHhRPbkNsaWVudEl0ZW1TZWxlY3RlZAVUd3NBdXRvQ29tcGxldGVfanNfc2VsZWN0ZWRfY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRG92ZXJfd3NBdXRvQ29tcGxldGUxHhJPbkNsaWVudFBvcHVsYXRpbmcFSFNob3dBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaERvdmVyX3dzQXV0b0NvbXBsZXRlMWQCCQ8PFgIfBgUpY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9idG5TZWFyY2hkFgQCAw8PZBYEHwcFSkhpZGVBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxHwgFXXJldHVybiBBdXRvQ29tcGxldGVDaGVja0RlbGV0ZShldmVudCwgJ2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfaGRuVmFsdWUnKWQCBQ8WBh8JBVhBdXRvQ29tcGxldGVfQ2xpZW50UG9wdWxhdGVkX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxHwoFVndzQXV0b0NvbXBsZXRlX2pzX3NlbGVjdGVkX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxHwsFSlNob3dBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxZAIND2QWBAIBDxBkEBUGFdeh15XXkteZINeT15nXldeg15nXnQzXqdeQ15nXnNeq15QP15TXptei16og15fXldenFteU16bXoteqINeQ15kg15DXnteV158a15TXptei15Qg15zXodeT16gg15TXmdeV150j15TXptei15Qg15zXodeT16gg15nXldedINeb15XXnNec16oVBgEwATEBMgEzATQCMTUUKwMGZ2dnZ2dnZGQCCQ8PZBYCHwUFyAFpZiAoKGV2ZW50LndoaWNoICYmIGV2ZW50LndoaWNoID09IDEzKSB8fCAoZXZlbnQua2V5Q29kZSAmJiBldmVudC5rZXlDb2RlID09IDEzKSkgICAgIHtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9idG5TZWFyY2gnKS5jbGljaygpO3JldHVybiBmYWxzZTt9ICAgICBlbHNlIHJldHVybiB0cnVlO2QCDw8PFgIeBERhdGUGAABgHGmBzAhkFgJmD2QWAmYPZBYCAgEPZBYEZg9kFgpmD2QWAgIBDw8WAh8EBQQyMDEwFgIfCAVVcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZEZyb20nKWQCAg9kFgICAQ8PFgIfBAUBMhYCHwgFVXJldHVybiBEYXRlUGlja2VyRGVsZXRlKGV2ZW50LCAnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRGF0ZXNQZXJpb2RGcm9tJylkAgQPZBYCAgEPDxYCHwQFAjIyFgIfCAVVcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZEZyb20nKWQCBg9kFgICAQ8WAh8EBQbXqdeg15lkAgcPZBYCAgEPDxYCHwQFCjIyLzAyLzIwMTAWBB8IBQ92YWxpZERhdGUodGhpcykfBwVJaXNEYXRlKHRoaXMsJ2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaERhdGVzUGVyaW9kRnJvbV9sYmxNc2cnKWQCAQ9kFgJmD2QWAmYPDxYCHwQFFteXJyDXkdeQ15PXqCDXlNeq16ki16JkZAIRDw8WAh8MBgAAYBxpgcwIZBYCZg9kFgJmD2QWAgIBD2QWBGYPZBYKZg9kFgICAQ8PFgIfBAUEMjAxMBYCHwgFU3JldHVybiBEYXRlUGlja2VyRGVsZXRlKGV2ZW50LCAnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRGF0ZXNQZXJpb2RUbycpZAICD2QWAgIBDw8WAh8EBQEyFgIfCAVTcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZFRvJylkAgQPZBYCAgEPDxYCHwQFAjIyFgIfCAVTcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZFRvJylkAgYPZBYCAgEPFgIfBAUG16nXoNeZZAIHD2QWAgIBDw8WAh8EBQoyMi8wMi8yMDEwFgQfCAUPdmFsaWREYXRlKHRoaXMpHwcFR2lzRGF0ZSh0aGlzLCdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZFRvX2xibE1zZycpZAIBD2QWAmYPZBYCZg8PFgIfBAUW15cnINeR15DXk9eoINeU16rXqSLXomRkAhUPEA8WAh4LXyFEYXRhQm91bmRnZBAVARDXlNeb16DXodeqINeUIDE4FQECMTgUKwMBZ2RkAhkPDxYCHgtQb3N0QmFja1VybAUlL2Vwcm90b2NvbC9QVUJMSUMvU2VhcmNoUEVPbmxpbmUuYXNweGRkAhsPDxYCHw4FJS9lcHJvdG9jb2wvUFVCTElDL1NlYXJjaFBFT25saW5lLmFzcHhkZAIdDw8WBB8EBTfXnNeQINeg157XpteQ15Ug16rXldem15DXldeqINec15fXmdek15XXqSDXlNee15HXlden16kuHgdWaXNpYmxlaGRkAgkPZBYGAgEPDxYCHwQFYSDXnteZ15zXlFzXmdedOiA8Yj7XkDwvYj4sICAgICAgICDXkdeY15XXldeXINeq15DXqNeZ15vXmdedOiA8Yj7Xni0yMi8wMi8yMDEwINei15MtMjIvMDIvMjAxMDwvYj5kZAIDDw8WAh8EBQEwZGQCBw8PFgIfBGVkZAILDw8WBh8EBRzXl9eW15XXqCDXnNee16HXmiDXl9eZ16TXldepHw4FJS9lcHJvdG9jb2wvUFVCTElDL1NlYXJjaFBFT25saW5lLmFzcHgfD2hkZBgBBR5fX0NvbnRyb2xzUmVxdWlyZVBvc3RCYWNrS2V5X18WCQU4Y3RsMDAkQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlciRzcmNoQ0tfaW50ZXJydXB0X3NwZWFrZXIFMWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkcmRvU2VhcmNoQnlOdW1iZXIFMWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkcmRvU2VhcmNoQnlOdW1iZXIFL2N0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkcmRvU2VhcmNoQnlUZXh0BTFjdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hfcmRvX1llc2hpdml0BTFjdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hfcmRvX1llc2hpdml0BS5jdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hfcmRvX1RvcmltBTxjdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hEYXRlc1BlcmlvZEZyb20kYnRuUG9wVXAFOmN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkc3JjaERhdGVzUGVyaW9kVG8kYnRuUG9wVXCpRkP1sigDyMUEQRUVvHjI2IVBFw%3D%3D&ctl00%24ContentPlaceHolderWrapper%24STATUS=srch_rdo_Torim&ctl00%24ContentPlaceHolderWrapper%24SearchSubjectRDO=rdoSearchByText&ctl00%24ContentPlaceHolderWrapper%24btnSearch=%D7%97%D7%A4%D7%A9&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtDate='+from_day+'%2F'+from_month+'%2F'+from_year+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtDay='+from_day+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtMonth='+from_month+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtYear='+from_year+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtDate='+to_day+'%2F'+to_month+'%2F'+to_year+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtDay='+to_day+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtMonth='+to_month+'&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtYear='+to_year+'&ctl00%24ContentPlaceHolderWrapper%24srchDover%24hdnValue=&ctl00%24ContentPlaceHolderWrapper%24srchDover%24myTextBox=&ctl00%24ContentPlaceHolderWrapper%24srchExcludeFreeText=&ctl00%24ContentPlaceHolderWrapper%24srchFreeText='+search_text+'&ctl00%24ContentPlaceHolderWrapper%24srchKnesset=18&ctl00%24ContentPlaceHolderWrapper%24srchManager%24hdnValue=&ctl00%24ContentPlaceHolderWrapper%24srchManager%24myTextBox=&ctl00%24ContentPlaceHolderWrapper%24srchSubject=&ctl00%24ContentPlaceHolderWrapper%24srchSubjectType=0&ctl00%24ContentPlaceHolderWrapper%24srch_SubjectNumber=&hiddenInputToUpdateATBuffer_CommonToolkitScripts=1'
            page = urllib2.urlopen(url,params).read()
            m = re.search('ProtEOnlineLoad\((.*), \'false\'\);', page)
            if not m:
                logger.debug("couldn't find vote in synched protocol\nvote.id=%s\nvote.title=%s\nsearch_text=%s", str(v.id), v.title, search_text)
                return
            l = Link(title=u'פרוטוקול מסונכרן (וידאו וטקסט) של הישיבה', url='http://online.knesset.gov.il/eprotocol/PLAYER/PEPlayer.aspx?ProtocolID=%s' % m.group(1), content_type=ContentType.objects.get_for_model(v), object_pk=str(v.id))
            l.save()
        except Exception:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            logger.error("%s%s", ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)), '\nsearch_text='+search_text.encode('utf8')+'\nvote.title='+v.title.encode('utf8'))

    def check_vote_mentioned_in_cm(self, v, cm):
        m = v.title[v.title.find(' - ')+2:]
        v_search_text = self.get_search_string(m.encode('utf8'))
        cm_search_text = self.get_search_string(cm.protocol_text.encode('utf8')).replace('\n','')
        if cm_search_text.find(v_search_text)>=0:
            cm.votes_mentioned.add(v)

    def find_votes_in_cms(self):
        for cm in CommitteeMeeting.objects.all():
            for v in Vote.objects.all():
                self.check_vote_mentioned_in_cm(v, cm)

    def get_protocols_page(self, page, page_num):
        logger.debug('get_protocols_page. page_num=%d' % page_num)
        FILES_BASE_URL = "http://www.knesset.gov.il/protocols/"
        res = []
        max_linked_page = max([int(r) for r in re.findall("'Page\$(\d*)",page)])
        last_page = False
        if max_linked_page < page_num:
            last_page = True

        # trim the page to the results part
        start = page.find(r'id="gvProtocol"')
        end = page.find(r'javascript:__doPostBack')
        page = page[start:end]
        date_text = ''
        comittee = ''
        subject = ''
        # find interesting parts
        matches = re.findall(r'<span id="gvProtocol(.*?)</span>|OpenDoc(.*?)\);',page, re.DOTALL)
        for (span,link) in matches:
            if len(span): # we are parsing a matched span - committee info
                if span.find(r'ComName')>0:
                    comittee = span[span.find(r'>')+1:]
                if span.find(r'lblDate')>0:
                    date_text = span[span.find(r'>')+1:]
                if span.find(r'lblSubject')>0:
                    if span.find(r'<Table')>0: # this subject is multiline so they show it a a table
                        subject = ' '.join(re.findall(r'>([^<]*)<',span)) # extract text only from all table elements
                    else:
                        subject = span[span.find(r'>')+1:] # no table, just take the text
            else: # we are parsing a matched link - comittee protocol url
                if (link.find(r'html')>0)or(link.find(r'rtf')>0):
                    html_url = FILES_BASE_URL + re.search(r"'\.\./([^']*)'", link).group(1)
                    res.append([date_text, comittee, subject, html_url]) # this is the last info we need, so add data to results
                    date_text = ''
                    comittee = ''
                    subject = ''
        return (last_page, res)

    def get_protocols(self, max_page=10):
        logger.debug('get_protocols. max_page=%d' % max_page)
        SEARCH_URL = "http://www.knesset.gov.il/protocols/heb/protocol_search.aspx"
        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        committees_aliases = []
        for c in Committee.objects.all():
            if c.aliases:
                committees_aliases += map(lambda x: (c, x), c.aliases.split(","))

        urllib2.install_opener(opener)


        # get the search page to extract legal "viewstate" and "event validation" strings. need to pass them so the search will work
        page = urllib2.urlopen(SEARCH_URL).read().decode('windows-1255').encode('utf-8')

        event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
        view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')

        # define date range
        params = "__EVENTTARGET=DtFrom&__EVENTARGUMENT=&__LASTFOCUS=&__VIEWSTATE=%s&ComId=-1&knesset_id=-1&DtFrom=24%%2F02%%2F2009&DtTo=&subj=&__EVENTVALIDATION=%s" % (view_state, event_validation)
        page = urllib2.urlopen(SEARCH_URL,params).read().decode('windows-1255').encode('utf-8')
        event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
        view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')

        # hit the search
        params = "btnSearch=%%E7%%E9%%F4%%E5%%F9&__EVENTTARGET=&__EVENTARGUMENT=&__LASTFOCUS=&__VIEWSTATE=%s&ComId=-1&knesset_id=-1&DtFrom=24%%2F02%%2F2009&DtTo=&subj=&__EVENTVALIDATION=%s" % (view_state, event_validation)
        page = urllib2.urlopen(SEARCH_URL,params).read().decode('windows-1255').encode('utf-8')
        event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
        view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')
        page_num = 1
        (last_page, page_res) = self.get_protocols_page(page, page_num)
        res = page_res[:]

        mk_names = []
        mks = []
        mk_persons = Person.objects.filter(mk__isnull=False).select_related('mk')
        mks.extend([person.mk for person in mk_persons])
        mk_aliases = PersonAlias.objects.filter(person__in=mk_persons)
        mk_names.extend(mk_persons.values_list('name',flat=True))
        mk_names.extend(mk_aliases.values_list('name',flat=True))
        mks.extend([alias.person.mk for alias in mk_aliases])
        while (not last_page) and (page_num < max_page):
            page_num += 1
            params = "__EVENTTARGET=gvProtocol&__EVENTARGUMENT=Page%%24%d&__LASTFOCUS=&__VIEWSTATE=%s&ComId=-1&knesset_id=-1&DtFrom=24%%2F02%%2F2009&DtTo=&subj=&__EVENTVALIDATION=%s" % (page_num, view_state, event_validation)
            page = urllib2.urlopen(SEARCH_URL,params).read().decode('windows-1255').encode('utf-8')
            # update EV and VS
            event_validation = urllib2.quote(re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', page).group(1)).replace('/','%2F')
            view_state = urllib2.quote(re.search(r'id="__VIEWSTATE" value="([^"]*)"', page).group(1)).replace('/','%2F')
            # parse the page
            (last_page, page_res) = self.get_protocols_page(page, page_num)
            res.extend(page_res)

        logger.debug('res contains %d entries' % len(res))

        for (date_string, com, topic, link) in res:
            (c, created) = Committee.objects.get_or_create(name=com)
            if created:
                c.save()
            r = re.search("(\d\d)/(\d\d)/(\d\d\d\d)", date_string)
            d = datetime.date(int(r.group(3)), int(r.group(2)), int(r.group(1)))
            if CommitteeMeeting.objects.filter(committee=c, date=d, topics=topic, date_string=date_string).count():
                cm = CommitteeMeeting.objects.filter(committee=c, date=d, topics=topic, date_string=date_string)[0]
                logger.debug('cm %d already exists' % cm.id)
                if not cm.bg_material: #committee meeting still has no bg - hack to get old bg material into db
                    self.get_bg_material(cm)
                continue
            elif CommitteeMeeting.objects.filter(src_url=link).count():
                cm = CommitteeMeeting.objects.get(src_url=link)
                logger.debug('cm %d is being updated' % cm.id)
                if date_string != cm.date_string:
                    cm.date_string = date_string
                    logger.debug('updated date_string')
                if d != cm.date:
                    cm.date = d
                    logger.debug('updated date')
                if topic != cm.topics:
                    cm.topics=topic
                    logger.debug('updated topics')
                if link != cm.src_url:
                    cm.src_url = link
                    logger.debug('updated src_url')
            else:
                cm = CommitteeMeeting.objects.create(committee=c, date=d, topics=topic, date_string=date_string, src_url=link)
                logger.debug('cm %d created' % cm.id)
            updated_protocol = False
            if not cm.protocol_text:
                cm.protocol_text = self.get_committee_protocol_text(link)
                # check if the protocol is from the wrong commitee
                for i in committees_aliases:
                    if i[1] in cm.protocol_text[:300]:
                        cm.committee = i[0]
                        break
                updated_protocol = True

            cm.save()

            if updated_protocol:
                cm.create_protocol_parts()

            self.find_attending_members(cm, mks, mk_names)

            self.get_bg_material(cm)

    def find_attending_members(self,cm, mks, mk_names):
        try:
            r = re.search("חברי הו?ועדה(.*?)(\n[^\n]*(רישום|רש(מים|מות|מו|מ|מת|ם|מה)|קצר(נים|ניות|ן|נית))[\s|:])".decode('utf8'),cm.protocol_text, re.DOTALL).group(1)
            s = r.split('\n')
            for (i,name) in enumerate(mk_names):
                for s0 in s:
                    if s0.find(name)>=0:
                        cm.mks_attended.add(mks[i])
        except Exception:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            logger.debug("%s%s", ''.join(traceback.format_exception(exceptionType,
                                                                    exceptionValue,
                                                                    exceptionTraceback)),
                         '\nCommitteeMeeting.id='+str(cm.id))
        logger.debug('meeting %d now has %d attending members' % (cm.id,
                                                                  cm.mks_attended.count()))

    def get_committee_protocol_text(self, url):
        logger.debug('get_committee_protocol_text. url=%s' % url)
        if url.find('html'):
            url = url.replace('html','rtf')
        file_str = StringIO()
        count = 0
        flag = True
        while count<10 and flag:
            try:
                file_str.write(urllib2.urlopen(url).read())
                flag = False
            except Exception:
                count += 1
        if flag:
            logger.error("can't open url %s. tried %d times" % (url, count))
        try:
            doc = Rtf15Reader.read(file_str)
        except Exception:
            return ''
        text = []
        attended_list = False
        for paragraph in doc.content:
            for sentence in paragraph.content:
                if 'bold' in sentence.properties and attended_list:
                    attended_list = False
                    text.append('')
                if 'מוזמנים'.decode('utf8') in sentence.content[0] and 'bold' in sentence.properties:
                    attended_list = True
                text.append(sentence.content[0])
        all_text = '\n'.join(text)
        return re.sub(r'\n:\n',r':\n',all_text)

    def get_bg_material(self,cm):
        links = cm.get_bg_material()
        if links:
            for i in links:
                l = Link.objects.create(url=i.get('url',''), title=i.get('title',''), content_object=cm)
                logger.debug('committee meeting link %d created' % l.id)


    def get_full_text(self,v):
        try:
            l = Link.objects.get(object_pk=str(v.id), title=u'מסמך הצעת החוק באתר הכנסת')
        except Exception:
            return
        try:
            if l.url.endswith('.rtf'):
                logger.info('get_full_text url=%s' % l.url)
                file_str = StringIO()
                file_str.write(urllib2.urlopen(l.url).read())
                doc = Rtf15Reader.read(file_str)
                content_list = []
                is_bold = False
                for j in [1,2]:
                    for i in range(len(doc.content[j].content)):
                        part = doc.content[j].content[i]
                        if 'bold' in part.properties:           # this part is bold
                            if not is_bold:                          # last part was not bold
                                content_list.append('<br/><b>')         # add new line and bold
                                is_bold = True                          # remember that we are now in bold
                            content_list.append(part.content[0]+' ') # add this part

                        else:                                   # this part is not bold
                            if len(part.content[0]) <= 1:           # this is a dummy node, ignore it
                                pass
                            else:                                   # this is a real node
                                if is_bold:                         # last part was bold. need to unbold
                                    content_list.append('</b>')
                                    is_bold = False
                                content_list.append('<br/>'+part.content[0]) #add this part in a new line

                    content_list.append('<br/>')

                v.full_text = ''.join(content_list)
                v.save()
        except Exception:
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            logger.error("%s%s", ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback)), '\nvote.title='+v.title.encode('utf8'))

    def dump_to_file(self):
        f = open('votes.tsv','wt')
        for v in Vote.objects.filter(time__gte=datetime.date(2009,2,24)):
            if (v.full_text_url != None):
                link = v.full_text_url.encode('utf-8')
            else:
                link = ''
            if (v.summary != None):
                summary = v.summary.encode('utf-8')
            else:
                summary = ''
            #for_ids = ",".join([str(m.id) for m in v.votes.filter(voteaction__type='for').all()])
            #against_ids = ",".join([str(m.id) for m in v.votes.filter(voteaction__type='against').all()])
            #f.write("%d\t%s\t%s\t%s\t%s\t%s\t%s\n" % (v.id,v.title.encode('utf-8'),v.time_string.encode('utf-8'),summary, link, for_ids, against_ids))
            f.write("%d\t%s\t%s\t%s\t%s\n" % (v.id, str(v.time), v.title.encode('utf-8'), summary, link))
        f.close()

        f = open('votings.tsv','wt')
        for v in Vote.objects.filter(time__gte=datetime.date(2009,2,24)):
            for va in v.voteaction_set.all():
                f.write("%d\t%d\t%s\n" % (v.id, va.member.id, va.type))
        f.close()

        f = open('members.tsv','wt')
        for m in Member.objects.filter(end_date__gte=datetime.date(2009,2,24)):
            f.write("%d\t%s\t%s\n" % (m.id, m.name.encode('utf-8'), m.current_party.__unicode__().encode('utf-8') if m.current_party != None else ''))
        f.close()

    def update_presence(self):
        logger.debug("update presence")
        try:
            (presence, valid_weeks) = parse_presence.parse_presence(filename=os.path.join(DATA_ROOT, 'presence.txt.gz'))
        except IOError:
            logger.error('Can\'t find presence file')
            return
        todays_timestamp = datetime.date.today().isocalendar()[:2]
        c = [b[0][0] for b in presence.values()]
        c.sort()
        min_timestamp = c[0]
        c = None

        for m in Member.objects.all():
            if m.id not in presence:
                logger.error('member %s (id=%d) not found in presence data', m.name, m.id)
                continue
            member_presence = dict(zip([b[0] for b in presence[m.id]], [b[1] for b in presence[m.id]]))

            if m.end_date:
                end_timestamp = m.end_date.isocalendar()[:2]
            else:
                end_timestamp = todays_timestamp

            current_timestamp = (m.start_date + datetime.timedelta(7)).isocalendar()[:2] # start searching on the monday after member joined the knesset
            if current_timestamp < min_timestamp: # we don't have info in the current file that goes back so far
                current_timestamp = min_timestamp

            while current_timestamp <= end_timestamp: # loop over weeks
                if current_timestamp in valid_weeks: # if we have valid data for this week
                    if current_timestamp in member_presence: # if this member was present this week
                        hours = member_presence[current_timestamp] # check how many hours
                    else:
                        hours = 0.0                                # not present at all this week = 0 hours
                    date = iso_to_gregorian(*current_timestamp, iso_day=0) # get real date of the week's monday
                    (wp,created) = WeeklyPresence.objects.get_or_create(member=m, date=date,
                                                                        defaults={'hours':hours})
                    wp.save()
                else:
                    date = iso_to_gregorian(*current_timestamp, iso_day=0)
                current_timestamp = (date+datetime.timedelta(8)).isocalendar()[:2]

    def update_private_proposal_content_html(self,pp):
        html = parse_remote.rtf(pp.source_url)
        if html:
            html = html.decode('utf8')
            if html.find(p_explanation)>=0:
                # this html is OK (should not happen)
                pass
            elif strong_explanation.search(html):
                # we already have the explanation highlighted, fix format
                html = strong_explanation.sub(p_explanation, html)
                logger.debug('fixed highlighting in private proposal %d in bill %d' % (pp.id, pp.bill.id))

            elif explanation.search(html):
                # highlight it
                html = explanation.sub(p_explanation, html)
                logger.debug('highlighed explanation in private proposal %d in bill %d' % (pp.id, pp.bill.id))

            pp.content_html = html
            pp.save()

    def parse_laws(self, private_proposals_days=None, last_booklet=None):
        """parse private proposal, knesset proposals and gov proposals
           private_proposals_days - override default "days-back" to look for in private proposals.
                                    should be the number of days back to look
           last_booklet - last knesset proposal booklet that you already have.
        """
        mks = Member.objects.values('id','name')
        for mk in mks:
            mk['cn'] = cannonize(mk['name'])

        # private laws
        logger.debug('parsing private laws')
        if private_proposals_days:
            days = private_proposals_days
        else:
            d = PrivateProposal.objects.aggregate(Max('date'))['date__max']
            if not d:
                d = datetime.date(2009,2,24)
            days = (datetime.date.today() - d).days


        proposals = parse_laws.ParsePrivateLaws(days)
        for proposal in proposals.laws_data:

            #if proposal['proposal_date'] < datetime.date(2009,02,24):
            #    continue

            # find the Law this poposal is updating, or create a new one
            law_name = proposal['law_name']
            if proposal['comment']:
                law_name += ' (%s)' % proposal['comment']

            (law, created) = Law.objects.get_or_create(title=law_name, merged_into=None)
            if created:
                law.save()
            if law.merged_into:
                law = law.merged_into

            # create the bill proposal
            if proposal['correction']:
                title = proposal['correction']
            else:
                title = "חוק חדש".decode('utf8')

            (pl,created) = PrivateProposal.objects.get_or_create(proposal_id=proposal['law_id'], knesset_id=proposal['knesset_id'],
                                                                 date=proposal['proposal_date'], source_url=proposal['text_link'],
                                                                 title=title, law=law)

            if created:
                pl.save()

                # update proposers and joiners
                for m0 in proposal['proposers']:
                    found = False
                    for mk in mks:
                        if cannonize(m0)==mk['cn']:
                            pl.proposers.add(Member.objects.get(pk=mk['id']))
                            found = True
                            break
                    if not found:
                        logger.warn(u"can't find proposer: %s" % m0)
                for m0 in proposal['joiners']:
                    found = False
                    for mk in mks:
                        if cannonize(m0)==mk['cn']:
                            pl.joiners.add(Member.objects.get(pk=mk['id']))
                            found = True
                            break
                    if not found:
                        logger.warn(u"can't find joiner: %s" % m0)

                # try to look for similar PPs already created:
                p = PrivateProposal.objects.filter(title=title,law=law).exclude(id=pl.id)
                b = None
                if p.count() > 0: # if there are, assume its the same bill
                    for p0 in p:
                        if p0.bill and not(b):
                            b = p0.bill
                if not(b): # if there are no similar proposals, or none of them had a bill
                    b = Bill(law=law, title=title, stage='1', stage_date=proposal['proposal_date'])  # create a new Bill, with only this PP.
                    b.save()
                for m in pl.proposers.all(): # add current proposers to bill proposers
                    b.proposers.add(m)
                for m in pl.joiners.all(): # add joiners to bill
                    b.joiners.add(m)
                pl.bill = b # assign this bill to this PP
                pl.save()

            if not pl.content_html:
                self.update_private_proposal_content_html(pl)

        # knesset laws
        logger.debug('parsing knesset laws')
        if not last_booklet:
            last_booklet = KnessetProposal.objects.aggregate(Max('booklet_number')).values()[0]
        if not last_booklet: # there were no KPs in the DB
            last_booklet = 200
        proposals = parse_laws.ParseKnessetLaws(last_booklet)
        for proposal in proposals.laws_data:
            #if not(proposal['date']) or proposal['date'] < datetime.date(2009,02,24):
            #    continue
            law_name = proposal['law'][:200] # protect against parsing errors that
                                             # create very long (and erroneous) law names
            (law, created) = Law.objects.get_or_create(title=law_name)
            if created:
                law.save()
            if law.merged_into:
                law = law.merged_into
            title = u''
            if proposal['correction']:
                title += proposal['correction']
            if proposal['comment']:
                title += ' ' + proposal['comment']
            if len(title)<=1:
                title = 'חוק חדש'.decode('utf8')
            (kl,created) = KnessetProposal.objects.get_or_create(booklet_number=proposal['booklet'], knesset_id=18,
                                                                 source_url=proposal['link'],
                                                                 title=title, law=law, date=proposal['date'])
            if created:
                kl.save()

            if not(proposal.has_key('original_ids')):
                logger.warn('Knesset proposal %d doesn\'t have original ids' % kl.id)
            else:
                for orig in proposal['original_ids']: # go over all originals in the document
                    try:
                        knesset_id = int(orig.split('/')[1]) # check if they are from current Knesset
                    except:
                        logger.warn('knesset proposal %d doesn\'t have knesset id' % kl.id)
                        continue
                    if knesset_id != 18:
                        logger.warn('knesset proposal %d has wrong knesset id (%d)' % (kl.id, knesset_id))
                        continue
                    orig_id = int(orig.split('/')[0]) # find the PP id
                    try:
                        pp = PrivateProposal.objects.get(proposal_id=orig_id) # find our PP object
                        kl.originals.add(pp) # and add a link to it
                        if pp.bill:
                            if not(kl.bill): # this kl stil has no bill associated with it, but PP has one
                                if KnessetProposal.objects.filter(bill=pp.bill).count(): # this bill is already taken by another KP
                                    logger.warn('Bill %d already has a KP, but should be assigned to KP %d' % (pp.bill.id, kl.id))
                                else:
                                    kl.bill = pp.bill
                                    kl.save()
                                    kl.bill.title = kl.title # update the title
                                    if kl.bill.stage_date < kl.date:
                                        kl.bill.stage_date = kl.date
                                        kl.bill.stage = '3'
                                    kl.bill.save()
                            else: # this kl already had a bill (from another PP)
                                kl.bill.merge(pp.bill) # merge them

                    except PrivateProposal.DoesNotExist:
                        logger.warn(u"can't find private proposal with id %d, referenced by knesset proposal %d %s %s" % (orig_id, kl.id, kl.title, kl.source_url))

            if not(kl.bill): # finished all original PPs, but found no bill yet - create a new bill
                b = Bill(law=law, title=title, stage='3', stage_date=proposal['date'])
                b.save()
                kl.bill = b
                kl.save()

        # parse gov proposals
        logger.debug('parsing gov laws')
        last_booklet = GovProposal.objects.aggregate(Max('booklet_number')).values()[0]
        if not last_booklet: # there were no KPs in the DB
            last_booklet = 500
        proposals = parse_laws.ParseGovLaws(last_booklet)
        proposals.parse_gov_laws()

    def find_proposals_in_other_data(self):
        """
        Find proposals in other data (committee meetings, votes).
        Calculates the cannonical names and then calls specific functions to do the actual work
        """
        gps = GovProposal.objects.values('id','title','law__title')
        for gp in gps:
            gp['t1'] = gp['law__title'] + ' ' + gp['title']
            gp['c1'] = cannonize(gp['law__title'] + gp['title'])
            gp['c2'] = cannonize(gp['title'] + gp['law__title'])

        kps = KnessetProposal.objects.values('id','title', 'law__title')
        for kp in kps:
            kp['t1'] = kp['law__title'] + ' ' + kp['title']
            kp['c1'] = cannonize(kp['law__title'] + kp['title'])
            kp['c2'] = cannonize(kp['title'] + kp['law__title'])

        pps = PrivateProposal.objects.values('id','title', 'law__title')
        for pp in pps:
            if pp['title']=='חוק חדש'.decode('utf8'):
                pp['c1'] = cannonize(pp['law__title'])
                pp['t1'] = pp['law__title']
            else:
                pp['c1'] = cannonize(pp['law__title'] + pp['title'])
                pp['t1'] = pp['law__title'] + ' ' + pp['title']
            pp['c2'] = cannonize(pp['title'] + pp['law__title'])

        self.find_proposals_in_committee_meetings(gps,kps,pps)
        self.find_proposals_in_votes(gps,kps,pps)

    def find_proposals_in_committee_meetings(self, gps, kps, pps):
        """
        Find Private proposals and Knesset proposals in committee meetings. update bills that are connected.
        kps and pps are dicts computed by find_proposals_in_other_data with canonical names.
        """

        d = datetime.date.today()-datetime.timedelta(60) # only look through cms in last 60 days.
        for cm in CommitteeMeeting.objects.filter(date__gt=d,committee__type='committee').exclude(protocol_text=None):
            c = cannonize(cm.protocol_text)
            for gp in gps:
                if c.find(gp['c1'])>=0 or c.find(gp['c2'])>=0:
                    p = GovProposal.objects.get(pk=gp['id'])
                    if cm not in p.committee_meetings.all():
                        p.committee_meetings.add(cm)
                        if p.bill:
                            p.bill.second_committee_meetings.add(cm)
                            p.bill.update_stage()
                        logger.debug('gov proposal %d found in cm %d' % (p.id,cm.id))
            for kp in kps:
                if c.find(kp['c1'])>=0 or c.find(kp['c2'])>=0:
                    p = KnessetProposal.objects.get(pk=kp['id'])
                    if cm not in p.committee_meetings.all():
                        p.committee_meetings.add(cm)
                        if p.bill:
                            p.bill.second_committee_meetings.add(cm)
                            p.bill.update_stage()
                        #print "add KP %d to CM %d" % (kp['id'], cm.id)
            for pp in pps:
                if c.find(pp['c1'])>=0 or c.find(pp['c2'])>=0:
                    p = PrivateProposal.objects.get(pk=pp['id'])
                    if cm not in p.committee_meetings.all():
                        p.committee_meetings.add(cm)
                        if p.bill:
                            p.bill.first_committee_meetings.add(cm)
                            p.bill.update_stage()
                        #print "add PP %d to CM %d" % (pp['id'], cm.id)

    def find_proposals_in_votes(self,gps,kps,pps):
        """
        Find Private proposals and Knesset proposals in votes. update bills that are connected.
        kps and pps are dicts computed by find_proposals_in_other_data with canonical names.
        """
        votes = Vote.objects.filter(title__contains='חוק').values('id','title')

        for v in votes:
            v['c'] = cannonize(v['title'])

            for gp in gps:
                if v['c'].find(gp['c1'])>=0:
                    p = GovProposal.objects.get(pk=gp['id'])
                    this_v = Vote.objects.get(pk=v['id'])
                    if this_v not in p.votes.all():
                        p.votes.add(this_v)
                        if p.bill:
                            p.bill.update_votes()
                        logger.debug('gov proposal %d found in vote %s' % (p.id,this_v.title))

            for kp in kps:
                if v['c'].find(kp['c1'])>=0:
                    p = KnessetProposal.objects.get(pk=kp['id'])
                    this_v = Vote.objects.get(pk=v['id'])
                    if this_v not in p.votes.all():
                        p.votes.add(this_v)
                        #print "add KP %d to Vote %d" % (kp['id'], this_v.id)
                        if p.bill:
                            p.bill.update_votes()

            for pp in pps:
                if v['c'].find(pp['c1'])>=0:
                    p = PrivateProposal.objects.get(pk=pp['id'])
                    this_v = Vote.objects.get(pk=v['id'])
                    if this_v not in p.votes.all():
                        p.votes.add(this_v)
                        #print "add PP %d to Vote %d" % (pp['id'], this_v.id)
                        if p.bill:
                            p.bill.update_votes()

    def merge_duplicate_laws(self):
        """Find and merge duplicate laws, and identical bills of each law"""

        laws = Law.objects.values('id','title','merged_into')

        for l in laws:
            l['c'] = cannonize(l['title'])

        for (i,l) in enumerate(laws):
            for j in range(i+1, len(laws)):
                l2 = laws[j]
                if l2['c']==l['c'] and l2['merged_into']==None and None==l['merged_into']:
                    law1 = Law.objects.get(pk=l['id'])
                    law2 = Law.objects.get(pk=l2['id'])
                    if law1.bills.count() > law2.bills.count():
                        law1.merge(law2)
                    else:
                        law2.merge(law1)

        for l in Law.objects.all():
            bills = l.bills.all()
            for (i,b) in enumerate(bills):
                for i2 in range(i+1,len(bills)):
                    if cannonize(b.title)==cannonize(bills[i2].title):
                        b.merge(bills[i2])

    def correct_votes_matching(self):
        """tries to find votes that are matched to bills in incorrect places
            (e.g approval votes attached as pre votes) and correct them

            """
        logger.debug("correct_votes_matching")
        for v in Vote.objects.filter(title__contains="אישור החוק"):
            if v.bills_pre_votes.count() == 1:
                logger.info("vote %d is approval but linked as pre. trying to fix" % v.id)
                bill_pre_voted = v.bills_pre_votes.all()[0]
                bills_approved = Bill.objects.filter(approval_vote=v)
                if bills_approved.count() == 1:
                    bill_approved = Bill.objects.filter(approval_vote=v)[0]
                    if bill_approved == bill_pre_voted: # its the same bill, just matched at wrong place
                        v.bills_pre_votes.remove(bill_pre_voted)
                    else:
                        logger.warn('vote %d is connected as both an approval (for bill %d) and pre (for bill %d)' % (v.id, bill_approved.id, bill_pre_voted.id))
                        continue
                if bills_approved.count() > 1:
                    logger.warn('vote %d is connected as an approval for more than 1 bill' % (v.id))
                    continue
                bill_pre_voted.approval_vote = v
                v.bills_pre_votes.remove(bill_pre_voted)
                bill_pre_voted.save()
                bill_pre_voted.update_stage()



    def update_mk_role_descriptions(self):
        mk_govt_roles = mk_roles_parser.parse_mk_govt_roles()
        for member in Member.objects.all():
            member.current_role_descriptions = None
            member.save()
        for (mk,roles) in mk_govt_roles.items():
            try:
                member = Member.objects.get(pk=mk)
                member.current_role_descriptions = unicode(roles)
                member.save()
            except Member.DoesNotExist:
                logger.warn('Found MK in govt roles with no matching MK: %s' % mk)
        mk_knesset_roles = mk_roles_parser.parse_mk_knesset_roles()
        for (mk,roles) in mk_knesset_roles.items():
            try:
                member = Member.objects.get(pk=mk)
                if not member.current_role_descriptions:
                    member.current_role_descriptions = unicode(roles)
                    member.save()
            except Member.DoesNotExist:
                logger.warn('Found MK in knesset roles with no matching MK: %s' % mk)

        intersection = set(mk_knesset_roles.keys()).intersection(set(mk_govt_roles.keys()))
        if len(intersection):
            logger.warn('Some MKs have roles in both knesset and govt: %s' % intersection)

    def update_gov_law_decisions(self, year=None, month=None):
        logger.debug("update_gov_law_decisions")
        if year==None or month==None:
            t = datetime.date.today()
            month = t.month-1
            if month==0:
                month=12
            year = t.year
        try:
            parser = ParseGLC(year-2000, month)
        except urllib2.URLError,e:
            logger.error(e)
            return
        for d in parser.scraped_data:
            logger.debug("parsed url: %s, subtitle: %s" %(d['url'],d['subtitle']))
            if d['subtitle']:
                m = re.search(r'ביום (\d+\.\d+.\d{4})'.decode('utf8'),d["subtitle"])
                if not m:
                    logger.warn("didn't find date on %s" % d['url'])
                    continue
                date = datetime.datetime.strptime(m.group(1),'%d.%m.%Y').date()
                (decision,created) = GovLegislationCommitteeDecision.objects.get_or_create(date=date,
                                               source_url=d['url'],title=d['title'],subtitle=d['subtitle'],
                                               text=d['decision'],number=int(d['number']))
                if created:
                    if re.search(r'להתנגד'.decode('utf8'), d['decision']):
                        decision.stand = -1
                    if re.search(r'לתמוך'.decode('utf8'), d['decision']):
                        decision.stand = 1
                    decision.save()

                # try to find a private proposal this decision is referencing
                try:
                    pp_id = int(re.search(r'פ/?(\d+)'.decode('utf8'),d['title']).group(1))
                    re.search(r'[2009|2010|2011|2012]'.decode('utf8'),d['title']).group(0)   # just make sure its about the right years
                    pp = PrivateProposal.objects.get(proposal_id=pp_id)
                    logger.debug("GovL.id = %d is matched to pp.id=%d, "
                                 "bill.id=%d" % (decision.id, pp.id,
                                                 pp.bill.id))
                    decision.bill = pp.bill
                    decision.save()
                except AttributeError: # one of the regex failed
                    logger.warn("GovL.id = %d doesn't contain PP or its about the wrong years" % decision.id)
                except PrivateProposal.DoesNotExist: # the PrivateProposal was not found
                    logger.warn('PrivateProposal %d not found but referenced in GovLegDecision %d' % (pp_id,decision.id))
                except PrivateProposal.MultipleObjectsReturned:
                    logger.warn('More than 1 PrivateProposal with proposal_id=%d' % pp_id)

    def handle_noargs(self, **options):

        all_options = options.get('all', False)
        download = options.get('download', False)
        load = options.get('load', False)
        process = options.get('process', False)
        dump_to_file = options.get('dump-to-file', False)
        update = options.get('update', False)
        laws = options.get('laws',False)
        committees = options.get('committees', False)

        if all_options:
            download = True
            load = True
            process = True
            dump_to_file = True

        if (all([not(all_options),not(download),not(load),not(process),
                 not(dump_to_file),not(update),not(laws), not(committees)])):
            print "no arguments found. doing nothing. \ntry -h for help.\n--all to run the full syncdata flow.\n--update for an online dynamic update."

        if download:
            print "beginning download phase"
            self.download_all()
            #self.get_laws_data()

        if load:
            print "beginning load phase"
            self.update_members_from_file()
            self.update_db_from_files()

        if process:
            print "beginning process phase"
            self.calculate_votes_importances()
            #self.calculate_correlations()

        if laws:
            self.parse_laws()
            self.find_proposals_in_other_data()
            self.merge_duplicate_laws()
            self.correct_votes_matching()

        if dump_to_file:
            print "writing votes to tsv file"
            self.dump_to_file()

        if update:
            self.update_votes()
            self.update_laws_data()
            self.update_presence()
            self.get_protocols()
            self.parse_laws()
            self.find_proposals_in_other_data()
            self.merge_duplicate_laws()
            self.update_mk_role_descriptions()
            self.update_mks_is_current()
            self.update_gov_law_decisions()
            self.correct_votes_matching()
            logger.debug('finished update')

        if committees:
            self.get_protocols()
            logger.debug('finished committees update')


def iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = datetime.date(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday()-1)
    return fourth_jan - delta

def iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(iso_day-1, 0, 0, 0, 0, 0, iso_week-1)
