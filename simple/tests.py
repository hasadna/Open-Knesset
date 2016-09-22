#encoding: utf-8
import re, os, datetime, cPickle,logging

from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from simple.management.commands import parse_knesset_bill_pdf
from simple.management.commands.parse_government_bill_pdf import pdftools
from simple.management.commands.parse_laws import GovProposalParser
from simple.management.commands.syncdata import Command as SyncDataCommand
from simple.management.commands.parse_laws import ParsePrivateLaws
from bs4 import BeautifulSoup

logger = logging.getLogger("open-knesset.simple")

TESTDATA = 'testdata'
GOV_BILL_TEST_FILE = os.path.join(TESTDATA, '566.pdf')
GOV_BILL_CORRECT_OUTPUT = os.path.join(TESTDATA, '566.correct.pickle')


class MockParsePrivateLaws(ParsePrivateLaws):

    def __init__(self):
        self.url =r"http://www.knesset.gov.il/privatelaw/Plaw_display.asp?lawtp=1"
        self.rtf_url=r"http://www.knesset.gov.il/privatelaw"
        self.laws_data=[]
        # the original function parses on init - this is not wanted when testing..
        # self.parse_pages_days_back(days_back)


class SyncdataTest(TestCase):

    def setUp(self):
        self.dir = os.path.abspath(os.path.join(settings.PROJECT_ROOT, 'tests'))

    def test_parse_knesset_bill_pdf_text(self):
        try:
            results = parse_knesset_bill_pdf.parse_pdf_text(os.path.join(self.dir,'knesset_proposal_366.txt'), "local-testing-cache/knesset_proposal_366.txt")
            self.assertEqual(len(results), 4)
            expected_date = datetime.date(2011,2,1)
            self.assertEqual(results[0]['date'], expected_date)
            expected_title = "הצעת חוק האזרחות (תיקון מס' 10) (ביטול אזרחות בשל הרשעה בעבירה), התשע\"א1102".decode('utf8')
            self.assertEqual(results[0]['title'], expected_title)
            expected_original = u'2377/18'
            self.assertEqual(results[0]['original_ids'][0], expected_original)
            expected_title = "הצעת חוק הביטוח הלאומי (תיקון מס' 126) (הארכת התכנית הניסיונית), התשע\"א1102".decode('utf8')
            self.assertEqual(results[3]['title'], expected_title)
        except IOError:
            pass

    def test_pdftools_version(self):
        if pdftools.PDFTOTEXT is None:
            logger.warning("no pdftotext on the system, skipping parse_government_bill_pdf tests")
            return
        self.assertTrue(pdftools.pdftotext_version_pass())

    # this test is not being run for now. need some fixes
    def dont_run__parse_government_bill_pdf(self):
        # make sure we have poppler - if not, just pass the test with an ignore
        self.assertTrue(os.path.exists(GOV_BILL_TEST_FILE), 'missing %s (cwd = %s)' % (GOV_BILL_TEST_FILE, os.getcwd()))
        self.assertTrue(os.path.exists(GOV_BILL_CORRECT_OUTPUT))
        prop = GovProposalParser(GOV_BILL_TEST_FILE)
        expected_result = cPickle.load(open(GOV_BILL_CORRECT_OUTPUT, 'r'))
        self.assertEqual(prop.to_unicode(True).encode('utf-8'), expected_result)

    def tearDown(self):
        pass


class SyncDataLawsTest(TestCase):

    def test_parse_laws_page(self):
        with open(os.path.join(os.path.dirname(__file__), '../testdata/laws_page.html'), 'rb') as f:
            page = f.read()
        names, exps, links = SyncDataCommand().parse_laws_page(page)
        # all the law names
        self.assertEqual(names[0], u'חוק יום העלייה, התשע”ו–2016'.encode('utf-8'))
        self.assertEquals(names[1], u'חוק מיסוי מקרקעין (שבח ורכישה) (תיקון מס` 87), התשע”ו–2016'.encode('utf-8'))
        # TODO: find out why exp is always empty and what is it
        self.assertEqual(exps[0], '')
        self.assertEqual(exps[1], '')
        # all the law links
        self.assertEqual(links[0], 'http://www.knesset.gov.il/privatelaw/data/20/3/632_3_1.rtf')
        self.assertEqual(links[1], 'http://www.knesset.gov.il/privatelaw/data/20/3/1036_3_1.rtf')

    def test_parse_private_laws(self):
        ppl = MockParsePrivateLaws()
        with open(os.path.join(os.path.dirname(__file__), '../testdata/private_laws_page.html')) as f:
            html = f.read()
        soup = BeautifulSoup(html)
        ppl.parse_private_laws_page(soup)
        self.assertDictEqual(
            {
                'comment': None,
                'text_link': u'http://www.knesset.gov.il/privatelaw/data/20/2785.rtf',
                'joiners': [u' ONMOUSEOVER="popup(\''],
                'law_id': 2785,
                'proposal_date': datetime.date(2016, 3, 14),
                'law_full_title': u'הצעת חוק מימון מפלגות (תיקון - הגדרת גוף פעיל בבחירות), התשע"ו-2016',
                'law_name': u'חוק מימון מפלגות',
                'law_year': u' התשע"ו-2016',
                'knesset_id': 20,
                'proposers': [
                    u'וד ביטן<br>נאוה בוקר<br>יואב קיש<br>אמיר אוחנה</br></br></br>'
                ],
                'correction': u'תיקון - הגדרת גוף פעיל בבחירות'
            },
            ppl.laws_data[0]
        )
        self.assertDictEqual(
            {
                'comment': None,
                'text_link': u'http://www.knesset.gov.il/privatelaw/data/20/3083.rtf',
                'joiners': [
                    u' ONMOUSEOVER="popup(\''
                ],
                'law_id': 3083,
                'proposal_date': datetime.date(2016, 6, 20),
                'law_full_title': u"הצעת חוק-יסוד: הכנסת (תיקון - קבלת סעיף בחוק-יסוד שדרוש לביטולו או לשינויו רוב מיוחס)",
                'law_name': u"חוק-יסוד: הכנסת",
                'law_year': None,
                'knesset_id': 20,
                'proposers': [
                    u"ואל חסון<br/>מנואל טרכטנברג"
                ],
                'correction': u"תיקון - קבלת סעיף בחוק-יסוד שדרוש לביטולו או לשינויו רוב מיוחס",
            },
            ppl.laws_data[1]
        )





if __name__ == '__main__':
    # hack the sys.path to include knesset and the level above it
    import sys
    import os
    this_dir = os.path.dirname(os.path.realpath(sys.modules[__name__].__file__))
    sys.path.append(os.path.join(this_dir, '../'))
    sys.path.append(os.path.join(this_dir, '../../'))
    # test tester
    class Tester(SyncdataTest):
        def runTest(self, *args, **kw):
            pass
    Tester().test_parse_government_bill_pdf()
