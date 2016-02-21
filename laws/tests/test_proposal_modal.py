# encoding: utf-8
#

from datetime import datetime

from django.test import TestCase

from laws.models import Bill, KnessetProposal

just_id = lambda x: x.id
APP = 'laws'


class ProposalModelTest(TestCase):
    def setUp(self):
        super(ProposalModelTest, self).setUp()
        self.bill = Bill.objects.create(stage='1', title='bill 1', popular_name="The Bill")
        self.kp_1 = KnessetProposal.objects.create(booklet_number=2,
                                                   bill=self.bill,
                                                   date=datetime(2005, 1, 22),
                                                   )

    def tearDown(self):
        super(ProposalModelTest, self).tearDown()

    def testContent(self):
        self.assertEqual(self.kp_1.get_explanation(), '')
        self.kp_1.content_html = 'yippee!'
        self.assertEqual(self.kp_1.get_explanation(), 'yippee!')
        self.kp_1.content_html = '''
<p>דברי הסבר</p>
<p>מטרת</p><p>---------------------------------</p>
                               '''.decode('utf8')
        self.assertEqual(self.kp_1.get_explanation(), u'<p>מטרת</p>')

    def tearDown(self):
        self.kp_1.delete()
        self.bill.delete()
