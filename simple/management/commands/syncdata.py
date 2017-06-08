# -*- coding: utf-8 -*-

import datetime
import gzip
import logging
import os
import re

import time
import traceback
import urllib
import urllib2
from cStringIO import StringIO
from optparse import make_option

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from okscraper_django.management.base_commands import NoArgsDbLogCommand

from pyth.plugins.rtf15.reader import Rtf15Reader

from committees.models import Committee, CommitteeMeeting
from knesset.utils import cannonize
from knesset.utils import send_chat_notification
from laws.models import (Vote, VoteAction, Bill, Law, PrivateProposal,
                         KnessetProposal, GovProposal, GovLegislationCommitteeDecision)
from links.models import Link
from mks.models import Member, Party, Membership, WeeklyPresence, Knesset

from persons.models import Person, PersonAlias

from simple.constants import SPECIAL_COMMITTEES_NAMES, SECOND_AND_THIRD_READING_LAWS_URL, CANONICAL_PARTY_ALIASES, \
    KNESSET_PROTOCOL_SEARCH_PAGE, KNESSET_SYNCED_PROTOCOL_PAGE, KNESSET_PRESENT_MKS_PAGE

from simple.parsers import mk_roles_parser
from simple.parsers import parse_laws
from simple.parsers import parse_remote
from simple.parsers.parse_gov_legislation_comm import ParseGLC
from simple.parsers import mk_info_html_parser as mk_parser
from simple.parsers import parse_presence
from syncdata_globals import p_explanation, strong_explanation, explanation

ENCODING = 'utf8'

DATA_ROOT = getattr(settings, 'DATA_ROOT',
                    os.path.join(settings.PROJECT_ROOT, os.path.pardir, os.path.pardir, 'data'))

logger = logging.getLogger(__name__)

try:
    SPECIAL_COMMITTEES = map(lambda x: dict(name=x, commitee=Committee.objects.get(name=x)),
                             SPECIAL_COMMITTEES_NAMES)
except:
    logger.warn("can't find special committees")
    SPECIAL_COMMITTEES = {}


class Command(NoArgsDbLogCommand):
    option_list = NoArgsDbLogCommand.option_list + (
        make_option('--all', action='store_true', dest='all',
                    help="runs all the syncdata sub processes (like --download --load --process --dump)"),

        make_option('--process', action='store_true', dest='process',
                    help="run post loading process."),

        make_option('--laws', action='store_true', dest='laws',
                    help="download and parse laws"),
        make_option(' ', action='store_true', dest='presence',
                    help="download and parse presence"),
        make_option('--update', action='store_true', dest='update',
                    help="online update of data."),
        make_option('--update-run-only', action='store', dest='update-run-only',
                    help="only run update for the provided functions. Should contain comma-seperated list of functions to run.")
    )
    help = "Downloads data from sources, parses it and loads it to the Django DB."

    requires_model_validation = False

    BASE_LOGGER_NAME = 'open-knesset'

    last_downloaded_vote_id = 0
    last_downloaded_member_id = 0

    def _handle_noargs(self, **options):
        global logger
        logger = self._logger

        all_options = options.get('all', False)

        process = options.get('process', False)

        update = options.get('update', False)
        laws = options.get('laws', False)
        presence = options.get('presence', False)

        if all_options:
            process = True

        selected_options = [all_options, process, update, laws, presence]
        if not any(selected_options):
            logger.error(
                "no arguments found. doing nothing. \ntry -h for help.\n--all to run the full syncdata flow.\n--update for an online dynamic update.")

        if process:
            logger.info("beginning process phase")
            self.calculate_votes_importances()
            # self.calculate_correlations()

        if laws:
            self.parse_laws()
            self.find_proposals_in_other_data()
            self.merge_duplicate_laws()
            self.correct_votes_matching()

        if presence:
            self.update_presence()

        if update:
            update_run_only = options.get('update-run-only', '')
            if update_run_only:
                try:
                    update_run_only = update_run_only.split(',')
                except AttributeError as e:
                    logger.exception("Error in syncdata update:")
            else:
                update_run_only = None
            for func in ['update_laws_data',
                         'update_presence',
                         'parse_laws',
                         'find_proposals_in_other_data',
                         'merge_duplicate_laws',
                         'update_mk_role_descriptions',
                         'update_mks_is_current',
                         # 'update_gov_law_decisions',
                         'correct_votes_matching']:
                # in case update_run_only is none, we run all stages
                if (update_run_only is None) or (func in update_run_only):
                    try:
                        logger.info('update: running %s', func)
                        self.__getattribute__(func).__call__()
                    except Exception as e:

                        send_chat_notification(__name__,
                                               "caught exception in one of the sync data update commands",
                                               {'exception': traceback.format_exc(), 'func': func})
                        # No need for manual exception formatting, logger exception takes care of that
                        logger.exception("Caught Exception in syncdata update phase %s", func)
            logger.info('finished update')

    def read_laws_page(self, index):

        url = '%s' % SECOND_AND_THIRD_READING_LAWS_URL
        data = urllib.urlencode({'RowStart': index})
        urlData = urllib2.urlopen(url, data)
        page = urlData.read().decode('windows-1255').encode('utf-8')
        return page

    def parse_laws_page(self, page):
        names = []
        exps = []
        links = []
        count = -1
        lines = page.split('\n')
        for line in lines:
            link = None
            r = re.search("""Href=\"(.*?)\">""", line)
            if r is not None:
                link = 'http://www.knesset.gov.il/privatelaw/' + r.group(1)
            r = re.search("""<td class="LawText1">(.*)""", line)
            if r is not None:
                name = r.group(1).replace("</td>", "").strip()
                if len(name) > 1 and name.find('span') < 0:
                    names.append(name)
                    if link:
                        links.append(link)
                    exps.append('')
                    count += 1
            if re.search("""arrResume\[\d*\]""", line) is not None:
                r = re.search('"(.*)"', line)
                if r is not None:
                    try:
                        exps[count] += r.group(1).replace('\t', ' ')
                    except:
                        pass

        return names, exps, links

    def download_laws(self):
        """
        returns an array of laws data: laws[i][0] - name, laws[i][1] - name for search, laws[i][2] - summary, laws[i][3] - link
        """
        laws = []
        for x in range(0, 79, 26):  # read 4 last laws pages
            # TODO: wtf! this works by confidence, hoping pages won't be missing or more then 4
            page = self.read_laws_page(x)
            (names, exps, links) = self.parse_laws_page(page)
            for (name, exp, link) in zip(names, exps, links):
                name_for_search = self.get_search_string(name)
                laws.append((name, name_for_search, exp, link))
        return laws

    def update_laws_data(self):
        logger.info("update laws data")
        laws = self.download_laws()
        logger.debug("finished downloading laws data")
        votes = Vote.objects.all().order_by('-time')[:200]
        # TODO: WTF! if this works, it is only by sheer coincidence
        # We are guessing that all new laws are part of the last 200 votes. why?
        for vote in votes:
            search_name = self.get_search_string(vote.title.encode('UTF-8'))
            for law in laws:
                if search_name.find(law[1]) >= 0:

                    vote.summary = law[2]
                    vote.save()
                    try:
                        vote_content_type = ContentType.objects.get_for_model(vote)
                        link, created = Link.objects.get_or_create(title=u'מסמך הצעת החוק באתר הכנסת', url=law[3],
                                                                   content_type=vote_content_type,
                                                                   object_pk=str(vote.id))
                        if created:
                            link.save()
                    except Exception as e:
                        logger.exception('Update law data exception')

            if not vote.full_text:
                self.get_approved_bill_text_for_vote(vote)
        logger.debug("finished updating laws data")

    def update_mks_is_current(self):
        """
        Set is_current=True if and only if mk is currently serving.
           This is done by looking at the presence page in the knesset website.
        """

        page = urllib2.urlopen(KNESSET_PRESENT_MKS_PAGE).read()
        mk_current_area = re.search('lbHowManyMKs2(.*)lbHowManyMKs', page, re.DOTALL)
        mks_ids = re.findall('mk_individual_id_t=(\d+)', mk_current_area.group())
        logger.info('found %d current mks' % len(mks_ids))
        if not len(mks_ids):
            logger.error('No current mks!')
        updated = Member.objects.filter(id__in=mks_ids).update(is_current=True)
        logger.info('updated %d mks to is_current=True' % updated)
        updated = Member.objects.exclude(id__in=mks_ids).update(is_current=False)
        logger.info('updated %d mks to is_current=False' % updated)

    def get_search_string(self, s):
        if isinstance(s, unicode):
            s = s.replace(u'\u201d', '').replace(u'\u2013', '')
        else:
            s = s.replace('\xe2\x80\x9d', '').replace('\xe2\x80\x93', '')
        return re.sub(r'["\(\) ,-]', '', s)

    heb_months = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר',
                  'דצמבר']

    def calculate_votes_importances(self):
        """
        Calculates votes importances. currently uses rule of thumb: number of voters against + number of voters for / 120.
        """
        for v in Vote.objects.all():
            v.importance = float(v.votes.filter(voteaction__type='for').count() + v.votes.filter(
                voteaction__type='against').count()) / 120
            v.save()

    def read_votes_page(self, voteId, retry=0):
        """
        Gets a votes page from the knesset website.
        returns a string (utf encoded)
        """
        url = "http://www.knesset.gov.il/vote/heb/Vote_Res_Map.asp?vote_id_t=%d" % voteId
        try:
            urlData = urllib2.urlopen(url)
            page = urlData.read().decode('windows-1255').encode('utf-8')
            time.sleep(2)
        except Exception as e:
            logger.warn(e)
            if retry < 5:
                logger.warn("waiting some time and trying again... (# of retries = %d)" % (retry + 1))
                page = self.read_votes_page(voteId, retry + 1)
            else:
                logger.exception("read votes page failed too many times")
                return None
        return page, url

    def read_member_votes(self, page, return_ids=False):
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
            if (re.match("""_R1""", i)):
                vote = "for"
            if (re.match("""_R2""", i)):
                vote = "against"
            if (re.match("""_R3""", i)):
                vote = "abstain"
            if (re.match("""_R4""", i)):
                vote = "no-vote"
            if (vote != ""):
                name = re.search("""DataText4>([^<]*)</a>""", i).group(1);
                name = re.sub("""&nbsp;""", " ", name)
                m_id = re.search("""mk_individual_id_t=(\d+)""", i).group(1)
                party = re.search("""DataText4>([^<]*)</td>""", i).group(1);
                party = re.sub("""&nbsp;""", " ", party)
                if (party == """ " """):
                    party = last_party
                else:
                    last_party = party
                if return_ids:
                    results.append((m_id, party, vote))
                else:
                    results.append((name, party, vote))

        return results

    def get_page_title(self, page):
        """
        Returns the title of a vote page
        """
        title = re.search("""<TITLE>([^<]*)</TITLE>""", page)
        return title.group(1)

    def get_vote_data(self, page):
        """
        Returns name, meeting number, vote number and date from a vote page
        """
        meeting_num = re.search("""מספר ישיבה: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        vote_num = re.search("""מספר הצבעה: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        name = re.search("""שם החוק: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        name = name.replace("\t", " ")
        name = name.replace("\n", " ")
        name = name.replace("\r", " ")
        name = name.replace("&nbsp;", " ")
        date = re.search("""תאריך: </td>[^<]*<[^>]*>([^<]*)<""", page).group(1)
        return \
            name, meeting_num, vote_num, date

    def find_synced_protocol(self, vote):
        search_text = ''
        try:

            to_day = from_day = str(vote.time.day)
            to_month = from_month = str(vote.time.month)
            to_year = from_year = str(vote.time.year)
            m = re.search(' - (.*),?', vote.title)
            if not m:
                logger.debug(u"couldn't create search string for vote\nvote.id=%s\nvote.title=%s\n", str(vote.id),
                             vote.title)
                return
            search_text = urllib2.quote(m.group(1).replace('(', '').replace(')', '').replace('`', '').encode('utf8'))

            # I'm really sorry for the next line, but I really had no choice:
            params = '__EVENTARGUMENT=&__EVENTTARGET=&__LASTFOCUS=&__PREVIOUSPAGE=bEfxzzDx0cPgMul_87gMIa3L4OOi0E21r4EnHaLHKQAsWXdde-10pzxRGZZaJFCK0&__SCROLLPOSITIONX=0&__SCROLLPOSITIONY=0&__VIEWSTATE=%2FwEPDwUKMjA3MTAzNTc1NA8WCB4VU0VTU0lPTl9SQU5ET01fTlVNQkVSAswEHhFPTkxZX0RBVEVTX1NFQVJDSGgeEFBSRVZJRVdfRFRfQ0FDSEUy5AQAAQAAAP%2F%2F%2F%2F8BAAAAAAAAAAQBAAAA7AFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5EaWN0aW9uYXJ5YDJbW1N5c3RlbS5JbnQzMiwgbXNjb3JsaWIsIFZlcnNpb249Mi4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XSxbU3lzdGVtLkRhdGEuRGF0YVRhYmxlLCBTeXN0ZW0uRGF0YSwgVmVyc2lvbj0yLjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODldXQMAAAAHVmVyc2lvbghDb21wYXJlcghIYXNoU2l6ZQADAAiRAVN5c3RlbS5Db2xsZWN0aW9ucy5HZW5lcmljLkdlbmVyaWNFcXVhbGl0eUNvbXBhcmVyYDFbW1N5c3RlbS5JbnQzMiwgbXNjb3JsaWIsIFZlcnNpb249Mi4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0IAAAAAAkCAAAAAAAAAAQCAAAAkQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5HZW5lcmljRXF1YWxpdHlDb21wYXJlcmAxW1tTeXN0ZW0uSW50MzIsIG1zY29ybGliLCBWZXJzaW9uPTIuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV1dAAAAAAseFEFQUFJOQ19DT1VOVEVSX0NBQ0hFMtgEAAEAAAD%2F%2F%2F%2F%2FAQAAAAAAAAAEAQAAAOABU3lzdGVtLkNvbGxlY3Rpb25zLkdlbmVyaWMuRGljdGlvbmFyeWAyW1tTeXN0ZW0uSW50MzIsIG1zY29ybGliLCBWZXJzaW9uPTIuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV0sW1N5c3RlbS5JbnQzMiwgbXNjb3JsaWIsIFZlcnNpb249Mi4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0DAAAAB1ZlcnNpb24IQ29tcGFyZXIISGFzaFNpemUAAwAIkQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5HZW5lcmljRXF1YWxpdHlDb21wYXJlcmAxW1tTeXN0ZW0uSW50MzIsIG1zY29ybGliLCBWZXJzaW9uPTIuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV1dCAAAAAAJAgAAAAAAAAAEAgAAAJEBU3lzdGVtLkNvbGxlY3Rpb25zLkdlbmVyaWMuR2VuZXJpY0VxdWFsaXR5Q29tcGFyZXJgMVtbU3lzdGVtLkludDMyLCBtc2NvcmxpYiwgVmVyc2lvbj0yLjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODldXQAAAAALFgJmD2QWAgIDD2QWAgIDD2QWCgIDDw8WAh4EVGV4dAX%2BBiBTRUxFQ1QgICAgIHRNZXRhRGF0YS5pSXRlbUlELCB0TWV0YURhdGEuaVRvcklELCB0TWV0YURhdGEuaUl0ZW1UeXBlLCB0TWV0YURhdGEuaVBhcmVudCwgdE1ldGFEYXRhLmlJdGVtUmF3SWQsIHRNZXRhRGF0YS5zVGl0bGUsICAgICAgICAgICAgICB0TWV0YURhdGEuc1RleHQsIHRNZXRhRGF0YS5pUGFnZSwgIHRNZXRhRGF0YS5pV29yZENvdW50ZXIsIHRNZXRhRGF0YS5pQnVsa051bSwgdE1ldGFEYXRhLmlFbGVtZW50SW5lZHhlciAgRlJPTSAgICAgICB0RGlzY3Vzc2lvbnMgSU5ORVIgSk9JTiAgICAgICAgICAgICB0VG9yaW0gT04gdERpc2N1c3Npb25zLmlEaXNjSUQgPSB0VG9yaW0uaURpc2NJRCBJTk5FUiBKT0lOICAgICAgICAgICAgIHRNZXRhRGF0YSBPTiB0VG9yaW0uaVRvciA9IHRNZXRhRGF0YS5pVG9ySUQgIFdIRVJFICB0VG9yaW0uYkhhc0ZpbmFsRG9jPTAgQU5EICAoQ09OVEFJTlMoc1RleHQsIE4nIteQ15nXqdeV16gg15TXl9eV16cg15TXptei16og15fXldenINeT15XXkyDXkdefINeS15XXqNeZ15XXnyDXqteZ16fXldefINeU16rXqSIi16IgMjAxMCIgICcpIE9SIENPTlRBSU5TKHNUaXRsZSwgTici15DXmdep15XXqCDXlNeX15XXpyDXlNem16LXqiDXl9eV16cg15PXldeTINeR158g15LXldeo15nXldefINeq15nXp9eV158g15TXqtepIiLXoiAyMDEwIiAgJykpIEFORCAgREFURURJRkYoREFZLCAnMi8yMi8yMDEwJyAsIHREaXNjdXNzaW9ucy5kRGF0ZSk%2BPTAgQU5EICBEQVRFRElGRihEQVksIHREaXNjdXNzaW9ucy5kRGF0ZSwgJzIvMjIvMjAxMCcpPj0wIEFORCAgdERpc2N1c3Npb25zLmlLbmVzc2V0IElOICgxOCkgQU5EICB0RGlzY3Vzc2lvbnMuaURpc2NUeXBlID0gMSBPUkRFUiBCWSBbaVRvcklEXSBERVNDLCBbaUVsZW1lbnRJbmVkeGVyXWRkAgUPDxYCHwRlZGQCBw9kFhYCAQ8PFgIfBAUi15fXmdek15XXqSDXkSLXk9eR16jXmSDXlNeb16DXodeqImRkAgMPD2QWAh4Jb25rZXlkb3duBcgBaWYgKChldmVudC53aGljaCAmJiBldmVudC53aGljaCA9PSAxMykgfHwgKGV2ZW50LmtleUNvZGUgJiYgZXZlbnQua2V5Q29kZSA9PSAxMykpICAgICB7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfYnRuU2VhcmNoJykuY2xpY2soKTtyZXR1cm4gZmFsc2U7fSAgICAgZWxzZSByZXR1cm4gdHJ1ZTtkAgcPDxYCHhRDdHJsRm9jdXNBZnRlclNlbGVjdAUpY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9idG5TZWFyY2hkFgQCAw8PZBYEHgZvbmJsdXIFSEhpZGVBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaERvdmVyX3dzQXV0b0NvbXBsZXRlMR4Hb25rZXl1cAVbcmV0dXJuIEF1dG9Db21wbGV0ZUNoZWNrRGVsZXRlKGV2ZW50LCAnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRG92ZXJfaGRuVmFsdWUnKWQCBQ8WBh4RT25DbGllbnRQb3B1bGF0ZWQFVkF1dG9Db21wbGV0ZV9DbGllbnRQb3B1bGF0ZWRfY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRG92ZXJfd3NBdXRvQ29tcGxldGUxHhRPbkNsaWVudEl0ZW1TZWxlY3RlZAVUd3NBdXRvQ29tcGxldGVfanNfc2VsZWN0ZWRfY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRG92ZXJfd3NBdXRvQ29tcGxldGUxHhJPbkNsaWVudFBvcHVsYXRpbmcFSFNob3dBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaERvdmVyX3dzQXV0b0NvbXBsZXRlMWQCCQ8PFgIfBgUpY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9idG5TZWFyY2hkFgQCAw8PZBYEHwcFSkhpZGVBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxHwgFXXJldHVybiBBdXRvQ29tcGxldGVDaGVja0RlbGV0ZShldmVudCwgJ2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfaGRuVmFsdWUnKWQCBQ8WBh8JBVhBdXRvQ29tcGxldGVfQ2xpZW50UG9wdWxhdGVkX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxHwoFVndzQXV0b0NvbXBsZXRlX2pzX3NlbGVjdGVkX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxHwsFSlNob3dBQ1BvcHVsYXRlX2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaE1hbmFnZXJfd3NBdXRvQ29tcGxldGUxZAIND2QWBAIBDxBkEBUGFdeh15XXkteZINeT15nXldeg15nXnQzXqdeQ15nXnNeq15QP15TXptei16og15fXldenFteU16bXoteqINeQ15kg15DXnteV158a15TXptei15Qg15zXodeT16gg15TXmdeV150j15TXptei15Qg15zXodeT16gg15nXldedINeb15XXnNec16oVBgEwATEBMgEzATQCMTUUKwMGZ2dnZ2dnZGQCCQ8PZBYCHwUFyAFpZiAoKGV2ZW50LndoaWNoICYmIGV2ZW50LndoaWNoID09IDEzKSB8fCAoZXZlbnQua2V5Q29kZSAmJiBldmVudC5rZXlDb2RlID09IDEzKSkgICAgIHtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9idG5TZWFyY2gnKS5jbGljaygpO3JldHVybiBmYWxzZTt9ICAgICBlbHNlIHJldHVybiB0cnVlO2QCDw8PFgIeBERhdGUGAABgHGmBzAhkFgJmD2QWAmYPZBYCAgEPZBYEZg9kFgpmD2QWAgIBDw8WAh8EBQQyMDEwFgIfCAVVcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZEZyb20nKWQCAg9kFgICAQ8PFgIfBAUBMhYCHwgFVXJldHVybiBEYXRlUGlja2VyRGVsZXRlKGV2ZW50LCAnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRGF0ZXNQZXJpb2RGcm9tJylkAgQPZBYCAgEPDxYCHwQFAjIyFgIfCAVVcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZEZyb20nKWQCBg9kFgICAQ8WAh8EBQbXqdeg15lkAgcPZBYCAgEPDxYCHwQFCjIyLzAyLzIwMTAWBB8IBQ92YWxpZERhdGUodGhpcykfBwVJaXNEYXRlKHRoaXMsJ2N0bDAwX0NvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXJfc3JjaERhdGVzUGVyaW9kRnJvbV9sYmxNc2cnKWQCAQ9kFgJmD2QWAmYPDxYCHwQFFteXJyDXkdeQ15PXqCDXlNeq16ki16JkZAIRDw8WAh8MBgAAYBxpgcwIZBYCZg9kFgJmD2QWAgIBD2QWBGYPZBYKZg9kFgICAQ8PFgIfBAUEMjAxMBYCHwgFU3JldHVybiBEYXRlUGlja2VyRGVsZXRlKGV2ZW50LCAnY3RsMDBfQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlcl9zcmNoRGF0ZXNQZXJpb2RUbycpZAICD2QWAgIBDw8WAh8EBQEyFgIfCAVTcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZFRvJylkAgQPZBYCAgEPDxYCHwQFAjIyFgIfCAVTcmV0dXJuIERhdGVQaWNrZXJEZWxldGUoZXZlbnQsICdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZFRvJylkAgYPZBYCAgEPFgIfBAUG16nXoNeZZAIHD2QWAgIBDw8WAh8EBQoyMi8wMi8yMDEwFgQfCAUPdmFsaWREYXRlKHRoaXMpHwcFR2lzRGF0ZSh0aGlzLCdjdGwwMF9Db250ZW50UGxhY2VIb2xkZXJXcmFwcGVyX3NyY2hEYXRlc1BlcmlvZFRvX2xibE1zZycpZAIBD2QWAmYPZBYCZg8PFgIfBAUW15cnINeR15DXk9eoINeU16rXqSLXomRkAhUPEA8WAh4LXyFEYXRhQm91bmRnZBAVARDXlNeb16DXodeqINeUIDE4FQECMTgUKwMBZ2RkAhkPDxYCHgtQb3N0QmFja1VybAUlL2Vwcm90b2NvbC9QVUJMSUMvU2VhcmNoUEVPbmxpbmUuYXNweGRkAhsPDxYCHw4FJS9lcHJvdG9jb2wvUFVCTElDL1NlYXJjaFBFT25saW5lLmFzcHhkZAIdDw8WBB8EBTfXnNeQINeg157XpteQ15Ug16rXldem15DXldeqINec15fXmdek15XXqSDXlNee15HXlden16kuHgdWaXNpYmxlaGRkAgkPZBYGAgEPDxYCHwQFYSDXnteZ15zXlFzXmdedOiA8Yj7XkDwvYj4sICAgICAgICDXkdeY15XXldeXINeq15DXqNeZ15vXmdedOiA8Yj7Xni0yMi8wMi8yMDEwINei15MtMjIvMDIvMjAxMDwvYj5kZAIDDw8WAh8EBQEwZGQCBw8PFgIfBGVkZAILDw8WBh8EBRzXl9eW15XXqCDXnNee16HXmiDXl9eZ16TXldepHw4FJS9lcHJvdG9jb2wvUFVCTElDL1NlYXJjaFBFT25saW5lLmFzcHgfD2hkZBgBBR5fX0NvbnRyb2xzUmVxdWlyZVBvc3RCYWNrS2V5X18WCQU4Y3RsMDAkQ29udGVudFBsYWNlSG9sZGVyV3JhcHBlciRzcmNoQ0tfaW50ZXJydXB0X3NwZWFrZXIFMWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkcmRvU2VhcmNoQnlOdW1iZXIFMWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkcmRvU2VhcmNoQnlOdW1iZXIFL2N0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkcmRvU2VhcmNoQnlUZXh0BTFjdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hfcmRvX1llc2hpdml0BTFjdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hfcmRvX1llc2hpdml0BS5jdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hfcmRvX1RvcmltBTxjdGwwMCRDb250ZW50UGxhY2VIb2xkZXJXcmFwcGVyJHNyY2hEYXRlc1BlcmlvZEZyb20kYnRuUG9wVXAFOmN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcldyYXBwZXIkc3JjaERhdGVzUGVyaW9kVG8kYnRuUG9wVXCpRkP1sigDyMUEQRUVvHjI2IVBFw%3D%3D&ctl00%24ContentPlaceHolderWrapper%24STATUS=srch_rdo_Torim&ctl00%24ContentPlaceHolderWrapper%24SearchSubjectRDO=rdoSearchByText&ctl00%24ContentPlaceHolderWrapper%24btnSearch=%D7%97%D7%A4%D7%A9&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtDate=' + from_day + '%2F' + from_month + '%2F' + from_year + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtDay=' + from_day + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtMonth=' + from_month + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodFrom%24txtYear=' + from_year + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtDate=' + to_day + '%2F' + to_month + '%2F' + to_year + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtDay=' + to_day + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtMonth=' + to_month + '&ctl00%24ContentPlaceHolderWrapper%24srchDatesPeriodTo%24txtYear=' + to_year + '&ctl00%24ContentPlaceHolderWrapper%24srchDover%24hdnValue=&ctl00%24ContentPlaceHolderWrapper%24srchDover%24myTextBox=&ctl00%24ContentPlaceHolderWrapper%24srchExcludeFreeText=&ctl00%24ContentPlaceHolderWrapper%24srchFreeText=' + search_text + '&ctl00%24ContentPlaceHolderWrapper%24srchKnesset=18&ctl00%24ContentPlaceHolderWrapper%24srchManager%24hdnValue=&ctl00%24ContentPlaceHolderWrapper%24srchManager%24myTextBox=&ctl00%24ContentPlaceHolderWrapper%24srchSubject=&ctl00%24ContentPlaceHolderWrapper%24srchSubjectType=0&ctl00%24ContentPlaceHolderWrapper%24srch_SubjectNumber=&hiddenInputToUpdateATBuffer_CommonToolkitScripts=1'
            page = urllib2.urlopen(KNESSET_PROTOCOL_SEARCH_PAGE, params).read()
            m = re.search('ProtEOnlineLoad\((.*), \'false\'\);', page)
            if not m:
                logger.debug(u"couldn't find vote in synced protocol\nvote.id=%s\nvote.title=%s\nsearch_text=%s",
                             str(vote.id), vote.title, search_text)
                return

            Link.objects.get_or_create(title=u'פרוטוקול מסונכרן (וידאו וטקסט) של הישיבה',
                                       url=KNESSET_SYNCED_PROTOCOL_PAGE % m.group(
                                           1),
                                       content_type=ContentType.objects.get_for_model(vote), object_pk=str(vote.id))

        except Exception:

            logger.exception(u'Exception in find synced protocol: vote id: %s search_text= %s' % (vote.pk, search_text))

    def check_vote_mentioned_in_cm(self, vote, cm):
        m = vote.title[vote.title.find(' - ') + 2:]
        v_search_text = self.get_search_string(m.encode('utf8'))
        cm_search_text = self.get_search_string(cm.protocol_text.encode('utf8')).replace('\n', '')
        if cm_search_text.find(v_search_text) >= 0:
            cm.votes_mentioned.add(vote)

    def find_votes_in_cms(self):
        for cm in CommitteeMeeting.objects.all():
            for v in Vote.objects.all():
                self.check_vote_mentioned_in_cm(v, cm)

    def get_approved_bill_text(self, url):
        """Retrieve the RTL file in the given url, assume approved bill file
           format, and return the text from the file.
        """
        file_str = StringIO()
        file_str.write(urllib2.urlopen(url).read())
        doc = Rtf15Reader.read(file_str)
        content_list = []
        is_bold = False
        for j in [1, 2]:
            for i in range(len(doc.content[j].content)):
                part = doc.content[j].content[i]
                if 'bold' in part.properties:  # this part is bold
                    if not is_bold:  # last part was not bold
                        content_list.append('<br/><b>')  # add newline and bold
                        is_bold = True  # remember that we are now in bold
                    content_list.append(part.content[0] + ' ')  # add this part

                else:  # this part is not bold
                    if len(part.content[0]) <= 1:
                        # this is a dummy node, ignore it
                        pass
                    else:  # this is a real node
                        if is_bold:  # last part was bold. need to unbold
                            content_list.append('</b>')
                            is_bold = False
                        # add this part in a new line
                        content_list.append('<br/>' + part.content[0])

            content_list.append('<br/>')
        return ''.join(content_list)

    def get_approved_bill_text_for_vote(self, vote):
        try:
            link = Link.objects.get(object_pk=str(vote.id),
                                    title=u'מסמך הצעת החוק באתר הכנסת')
        except Exception:
            return
        try:
            if link.url.endswith('.rtf'):
                logger.info(u'get_approved_bill_text_for_vote for vote %s url=%s' % (vote.id, link.url))
                vote.full_text = self.get_approved_bill_text(link.url)
                vote.save()
        except Exception as e:

            logger.exception(u'Exception with approved bill text for vote %s title=%s' % (vote.id, vote.title))

    def update_presence(self):
        logger.info("Starting to update presence")
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

        for member in Member.current_members.all():
            logger.info("Trying to update presence for %s" % member.pk)
            if member.id not in presence:
                logger.error('member %s (id=%d) not found in presence data', member.name, member.id)
                continue
            member_presence = dict(zip([b[0] for b in presence[member.id]], [b[1] for b in presence[member.id]]))

            end_timestamp = todays_timestamp

            start_date = member.start_date or datetime.datetime.utcnow()
            current_timestamp = (start_date + datetime.timedelta(7)).isocalendar()[
                                :2]  # start searching on the monday after member joined the knesset
            if current_timestamp < min_timestamp:  # we don't have info in the current file that goes back so far
                current_timestamp = min_timestamp

            while current_timestamp <= end_timestamp:  # loop over weeks
                if current_timestamp in valid_weeks:  # if we have valid data for this week
                    if current_timestamp in member_presence:  # if this member was present this week
                        hours = member_presence[current_timestamp]  # check how many hours
                    else:
                        hours = 0.0  # not present at all this week = 0 hours
                    date = iso_to_gregorian(*current_timestamp, iso_day=0)  # get real date of the week's monday
                    (wp, created) = WeeklyPresence.objects.get_or_create(member=member, date=date,
                                                                         defaults={'hours': hours})
                    wp.save()
                else:
                    date = iso_to_gregorian(*current_timestamp, iso_day=0)
                current_timestamp = (date + datetime.timedelta(8)).isocalendar()[:2]
        logger.info('Finished updating presence')


    def update_private_proposal_content_html(self, pp):
        html = parse_remote.rtf(pp.source_url)
        if html:
            html = html.decode('utf8')
            if html.find(p_explanation) >= 0:
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
           private_proposals_days - override default "days-back" to look for in
                                    private proposals.
                                    should be the number of days back to look
           last_booklet - last knesset proposal booklet that you already have.
        """
        current_knesset = Knesset.objects.current_knesset()
        mks = self._get_existing_cannonized_mks()

        # private laws
        logger.info('parsing private laws')
        if private_proposals_days:
            days = private_proposals_days
        else:
            d = PrivateProposal.objects.get_last_private_proposal_date()

            days = (datetime.date.today() - d).days

        proposals = parse_laws.ParsePrivateLaws(days)
        for proposal in proposals.laws_data:
            try:
                self._create_or_update_private_proposal_and_respective_law_and_bill(mks, proposal)
            except Exception:
                logger.exception(u'UnCaught Exception with private proposal dto %s' % proposal)

        logger.info('parsing knesset laws')
        if not last_booklet:
            last_booklet = KnessetProposal.objects.get_last_booklet()

        proposals = parse_laws.ParseKnessetLaws(last_booklet)
        for proposal in proposals.laws_data:
            try:
                self._create_or_update_knesset_proposal_and_respective_law_and_bill(current_knesset, proposal)
            except Exception:
                logger.exception(u'UnCaught Exception with knesset proposal dto %s' % proposal)

        # parse gov proposals
        logger.info('parsing gov laws')
        last_booklet = GovProposal.objects.get_last_booklet()

        # TODO: WTF? this does not do anything with the data!
        gov_proposals = parse_laws.ParseGovLaws(last_booklet)
        gov_proposals.parse_gov_laws()

    def _create_or_update_knesset_proposal_and_respective_law_and_bill(self, k, proposal):
        logger.info('Processing knesset law dto %s' % proposal)
        law_name = proposal['law'][:200]  # protect against parsing errors that
        # create very long (and erroneous) law names
        (law, created) = Law.objects.get_or_create(title=law_name)

        if law.merged_into:
            law = law.merged_into
        title = u''
        if proposal['correction']:
            title += proposal['correction']
        if proposal['comment']:
            title += ' ' + proposal['comment']
        if len(title) <= 1:
            title = 'חוק חדש'.decode('utf8')
        (kl, created) = KnessetProposal.objects.get_or_create(
            booklet_number=proposal['booklet'],
            knesset_id=k.number,
            source_url=proposal['link'],
            title=title,
            law=law,
            date=proposal['date'])

        if not (proposal.has_key('original_ids')):
            logger.warn('Knesset proposal %d doesn\'t have original ids' % kl.id)
        else:
            for orig in proposal['original_ids']:  # go over all originals in the document
                try:
                    knesset_id = int(orig.split('/')[1])  # check if they are from current Knesset
                except:
                    logger.warn('knesset proposal %d doesn\'t have knesset id' % kl.id)
                    continue
                if knesset_id != k.number:
                    logger.warn('knesset proposal %d has wrong knesset id (%d)' % (kl.id, knesset_id))
                    continue
                orig_id = int(orig.split('/')[0])  # find the PP id
                try:
                    original_private_proposals = PrivateProposal.objects.filter(proposal_id=orig_id)  # find our PP object
                    for pp in original_private_proposals:
                        kl.originals.add(pp)  # and add a link to it
                        if pp.bill:
                            if not kl.bill:  # this kl stil has no bill associated with it, but PP has one
                                if KnessetProposal.objects.filter(
                                        bill=pp.bill).count():  # this bill is already taken by another KP
                                    logger.warn('Bill %d already has a KP, but should be assigned to KP %d' % (
                                        pp.bill.id, kl.id))
                                else:
                                    kl.bill = pp.bill
                                    kl.save()
                                    kl.bill.title = kl.title  # update the title
                                    if kl.bill.stage_date < kl.date:
                                        kl.bill.stage_date = kl.date
                                        kl.bill.stage = '3'
                                    kl.bill.save()
                            else:  # this kl already had a bill (from another PP)
                                kl.bill.merge(pp.bill)  # merge them

                except PrivateProposal.DoesNotExist:
                    logger.warn(
                        u"can't find private proposal with id %d, referenced by knesset proposal %d %s %s" % (
                            orig_id, kl.id, kl.title, kl.source_url))

        if not kl.bill:  # finished all original PPs, but found no bill yet - create a new bill
            bill = Bill(law=law, title=title, stage='3', stage_date=proposal['date'])
            bill.save()
            kl.bill = bill
            kl.save()

    def _create_or_update_private_proposal_and_respective_law_and_bill(self, mks, proposal):
        # find the Law this poposal is updating, or create a new one
        logger.info(u'Processing private law dto %s' % proposal)
        law_name = proposal['law_name']
        if proposal['comment']:
            law_name += ' (%s)' % proposal['comment']
        (law, created) = Law.objects.get_or_create(title=law_name, merged_into=None)
        if law.merged_into:
            law = law.merged_into

        # create the bill proposal
        if proposal['correction']:
            title = proposal['correction']
        else:
            title = "חוק חדש".decode('utf8')
        (pl, created) = PrivateProposal.objects.get_or_create(proposal_id=proposal['law_id'],
                                                              knesset_id=proposal['knesset_id'],
                                                              date=proposal['proposal_date'],
                                                              source_url=proposal['text_link'],
                                                              title=title, law=law)
        if created:

            # update proposers and joiners
            for m0 in proposal['proposers']:
                cm0 = cannonize(m0)
                found = False
                for mk in mks:
                    if cm0 == mk['cn']:
                        pl.proposers.add(Member.objects.get(pk=mk['id']))
                        found = True
                        break
                if not found:
                    logger.warn(u"can't find proposer: %s (cannonized %s) law %s" % (m0,
                                                                                     cm0, pl))
            for m0 in proposal['joiners']:
                cm0 = cannonize(m0)
                found = False
                for mk in mks:
                    if cm0 == mk['cn']:
                        pl.joiners.add(Member.objects.get(pk=mk['id']))
                        found = True
                        break
                if not found:
                    logger.warn(u"can't find joiner: %s (cannonized %s) law %s" % (m0,
                                                                                   cm0, pl))

            # try to look for similar PPs already created:
            private_proposal = PrivateProposal.objects.filter(title=title, law=law).exclude(id=pl.id)
            bill = None
            if private_proposal.count() > 0:  # if there are, assume its the same bill
                for p0 in private_proposal:
                    if p0.bill and not bill:
                        bill = p0.bill
            if not bill:  # if there are no similar proposals, or none of them had a bill
                bill = Bill(law=law, title=title, stage='1',
                            stage_date=proposal['proposal_date'])  # create a new Bill, with only this PP.
                bill.save()
            for m in pl.proposers.all():  # add current proposers to bill proposers
                bill.proposers.add(m)
            for m in pl.joiners.all():  # add joiners to bill
                bill.joiners.add(m)
            pl.bill = bill  # assign this bill to this PP
            pl.save()
        if not pl.content_html:
            self.update_private_proposal_content_html(pl)

    def _get_existing_cannonized_mks(self):
        mks = list(Member.objects.values('id', 'name'))
        # add MK alias names, from person alias table
        mk_persons = Person.objects.filter(
            mk__isnull=False,
            mk__current_party__isnull=False).select_related('mk')
        mk_aliases = PersonAlias.objects.filter(person__in=mk_persons)
        for mk_alias in mk_aliases:
            mks.append({'id': mk_alias.person.mk_id,
                        'name': mk_alias.name})

        # pre-calculate cannonical represention of all names (without spaces,
        # and funcky chars - makes more robust comparisons)
        for mk in mks:
            mk['cn'] = cannonize(mk['name'])

        return mks

    def find_proposals_in_other_data(self):
        """
        Find proposals in other data (committee meetings, votes).
        Calculates the cannonical names and then calls specific functions to do the actual work
        """
        gps = GovProposal.objects.values('id', 'title', 'law__title')
        for gp in gps:
            gp['t1'] = gp['law__title'] + ' ' + gp['title']
            gp['c1'] = cannonize(gp['law__title'] + gp['title'])
            gp['c2'] = cannonize(gp['title'] + gp['law__title'])

        kps = KnessetProposal.objects.values('id', 'title', 'law__title')
        for kp in kps:
            kp['t1'] = kp['law__title'] + ' ' + kp['title']
            kp['c1'] = cannonize(kp['law__title'] + kp['title'])
            kp['c2'] = cannonize(kp['title'] + kp['law__title'])

        pps = PrivateProposal.objects.values('id', 'title', 'law__title')
        for pp in pps:
            if pp['title'] == 'חוק חדש'.decode('utf8'):
                pp['c1'] = cannonize(pp['law__title'])
                pp['t1'] = pp['law__title']
            else:
                pp['c1'] = cannonize(pp['law__title'] + pp['title'])
                pp['t1'] = pp['law__title'] + ' ' + pp['title']
            pp['c2'] = cannonize(pp['title'] + pp['law__title'])

        self.find_proposals_in_committee_meetings(gps, kps, pps)
        self.find_proposals_in_votes(gps, kps, pps)

    def find_proposals_in_committee_meetings(self, gps, kps, pps):
        """
        Find Private proposals and Knesset proposals in committee meetings. update bills that are connected.
        kps and pps are dicts computed by find_proposals_in_other_data with canonical names.
        """

        d = datetime.date.today() - datetime.timedelta(60)  # only look through cms in last 60 days.
        for cm in CommitteeMeeting.objects.filter(date__gt=d, committee__type='committee').exclude(protocol_text=None):
            c = cannonize(cm.protocol_text)
            for gp in gps:
                if c.find(gp['c1']) >= 0 or c.find(gp['c2']) >= 0:
                    p = GovProposal.objects.get(pk=gp['id'])
                    if cm not in p.committee_meetings.all():
                        p.committee_meetings.add(cm)
                        if p.bill:
                            p.bill.second_committee_meetings.add(cm)
                            p.bill.update_stage()
                        logger.debug('gov proposal %d found in cm %d' % (p.id, cm.id))
            for kp in kps:
                if c.find(kp['c1']) >= 0 or c.find(kp['c2']) >= 0:
                    p = KnessetProposal.objects.get(pk=kp['id'])
                    if cm not in p.committee_meetings.all():
                        p.committee_meetings.add(cm)
                        if p.bill:
                            p.bill.second_committee_meetings.add(cm)
                            p.bill.update_stage()

            for pp in pps:
                if c.find(pp['c1']) >= 0 or c.find(pp['c2']) >= 0:
                    p = PrivateProposal.objects.get(pk=pp['id'])
                    if cm not in p.committee_meetings.all():
                        p.committee_meetings.add(cm)
                        if p.bill:
                            p.bill.first_committee_meetings.add(cm)
                            p.bill.update_stage()

    def find_proposals_in_votes(self, gps, kps, pps):
        """
        Find Private proposals and Knesset proposals in votes. update bills that are connected.
        kps and pps are dicts computed by find_proposals_in_other_data with canonical names.
        """
        votes = Vote.objects.filter(title__contains='חוק').values('id', 'title')

        for v in votes:
            v['c'] = cannonize(v['title'])

            for gp in gps:
                if v['c'].find(gp['c1']) >= 0:
                    p = GovProposal.objects.get(pk=gp['id'])
                    this_v = Vote.objects.get(pk=v['id'])
                    if this_v not in p.votes.all():
                        p.votes.add(this_v)
                        if p.bill:
                            p.bill.update_votes()
                        logger.debug('gov proposal %d found in vote %s' % (p.id, this_v.title))

            for kp in kps:
                if v['c'].find(kp['c1']) >= 0:
                    p = KnessetProposal.objects.get(pk=kp['id'])
                    this_v = Vote.objects.get(pk=v['id'])
                    if this_v not in p.votes.all():
                        p.votes.add(this_v)
                        # print "add KP %d to Vote %d" % (kp['id'], this_v.id)
                        if p.bill:
                            p.bill.update_votes()

            for pp in pps:
                if v['c'].find(pp['c1']) >= 0:
                    p = PrivateProposal.objects.get(pk=pp['id'])
                    this_v = Vote.objects.get(pk=v['id'])
                    if this_v not in p.votes.all():
                        p.votes.add(this_v)

                        if p.bill:
                            p.bill.update_votes()

    def merge_duplicate_laws(self):
        """Find and merge duplicate laws, and identical bills of each law"""

        laws = Law.objects.values('id', 'title', 'merged_into')

        for l in laws:
            l['c'] = cannonize(l['title'])

        for (i, l) in enumerate(laws):
            for j in range(i + 1, len(laws)):
                l2 = laws[j]
                if l2['c'] == l['c'] and l2['merged_into'] == None and None == l['merged_into']:
                    law1 = Law.objects.get(pk=l['id'])
                    law2 = Law.objects.get(pk=l2['id'])
                    if law1.bills.count() > law2.bills.count():
                        law1.merge(law2)
                    else:
                        law2.merge(law1)

        for l in Law.objects.all():
            bills = l.bills.all()
            for (i, b) in enumerate(bills):
                for i2 in range(i + 1, len(bills)):
                    if cannonize(b.title) == cannonize(bills[i2].title):
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
                    if bill_approved == bill_pre_voted:  # its the same bill, just matched at wrong place
                        v.bills_pre_votes.remove(bill_pre_voted)
                    else:
                        logger.warn('vote %d is connected as both an approval (for bill %d) and pre (for bill %d)' % (
                            v.id, bill_approved.id, bill_pre_voted.id))
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
        for (mk, roles) in mk_govt_roles.items():
            try:
                member = Member.objects.get(pk=mk)
                member.current_role_descriptions = unicode(roles)
                member.save()
            except Member.DoesNotExist:
                logger.warn('Found MK in govt roles with no matching MK: %s' % mk)
        mk_knesset_roles = mk_roles_parser.parse_mk_knesset_roles()
        for (mk, roles) in mk_knesset_roles.items():
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
        # Deprecated - currently not in use
        logger.debug("update_gov_law_decisions")
        if year is None or month is None:
            t = datetime.date.today()
            month = t.month - 1
            if month == 0:
                month = 12
            year = t.year
        try:
            parser = ParseGLC(year - 2000, month)
        except urllib2.URLError as e:
            logger.exception('Error update gov law decisions')
            return
        for d in parser.scraped_data:
            logger.debug("parsed url: %s, subtitle: %s" % (d['url'], d['subtitle']))
            if d['subtitle']:
                m = re.search(r'ביום (\d+\.\d+.\d{4})'.decode('utf8'), d["subtitle"])
                if not m:
                    logger.warn("didn't find date on %s" % d['url'])
                    continue
                date = datetime.datetime.strptime(m.group(1), '%d.%m.%Y').date()
                (decision, created) = GovLegislationCommitteeDecision.objects.get_or_create(date=date,
                                                                                            source_url=d['url'],
                                                                                            title=d['title'],
                                                                                            subtitle=d['subtitle'],
                                                                                            text=d['decision'],
                                                                                            number=int(d['number']))
                if created:
                    if re.search(r'להתנגד'.decode('utf8'), d['decision']):
                        decision.stand = -1
                    if re.search(r'לתמוך'.decode('utf8'), d['decision']):
                        decision.stand = 1
                    decision.save()

                # try to find a private proposal this decision is referencing
                try:
                    pp_id = int(re.search(r'פ/?(\d+)'.decode('utf8'), d['title']).group(1))
                    re.search(r'[2009|2010|2011|2012]'.decode('utf8'), d['title']).group(
                        0)  # just make sure its about the right years
                    pp = PrivateProposal.objects.get(proposal_id=pp_id)
                    logger.debug("GovL.id = %d is matched to pp.id=%d, "
                                 "bill.id=%d" % (decision.id, pp.id,
                                                 pp.bill.id))
                    decision.bill = pp.bill
                    decision.save()
                except AttributeError:  # one of the regex failed
                    logger.warn("GovL.id = %d doesn't contain PP or its about the wrong years" % decision.id)
                except PrivateProposal.DoesNotExist:  # the PrivateProposal was not found
                    logger.warn(
                        'PrivateProposal %d not found but referenced in GovLegDecision %d' % (pp_id, decision.id))
                except PrivateProposal.MultipleObjectsReturned:
                    logger.warn('More than 1 PrivateProposal with proposal_id=%d' % pp_id)


def iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = datetime.date(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(iso_day - 1, 0, 0, 0, 0, 0, iso_week - 1)
