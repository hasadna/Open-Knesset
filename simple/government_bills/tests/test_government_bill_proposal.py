import datetime
import os

from django.test.testcases import SimpleTestCase

from simple.government_bills.parse_government_bill_pdf import GovProposalParser


class GovernmentBillProposalParserTestCase(SimpleTestCase):
    def setUp(self):
        super(GovernmentBillProposalParserTestCase, self).setUp()

    def tearDown(self):
        super(GovernmentBillProposalParserTestCase, self).setUp()

    def test_date_parsing_returns_correct_date_from_gov_proposals(self):
        filepath = os.path.dirname(__file__)
        full_filepath = os.path.join(filepath, '1075.pdf')
        parsed_page_date = GovProposalParser(full_filepath)
        parsed_date = parsed_page_date.get_date()
        self.assertEqual(parsed_date, datetime.date(2016, 8, 1))
