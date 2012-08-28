#encoding: utf-8
import re, os, datetime, cPickle,logging

from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from knesset.simple.management.commands import parse_knesset_bill_pdf
from knesset.simple.management.commands.parse_government_bill_pdf import pdftools
from knesset.simple.management.commands.parse_laws import GovProposalParser

logger = logging.getLogger("open-knesset.simple")

TESTDATA = 'testdata'
GOV_BILL_TEST_FILE = os.path.join(TESTDATA, '566.pdf')
GOV_BILL_CORRECT_OUTPUT = os.path.join(TESTDATA, '566.correct.pickle')

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
            expected_original = u'2377/18/\u05e4'
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
