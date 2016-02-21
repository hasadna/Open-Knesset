# encoding: utf-8
#

from datetime import datetime

from actstream import Action
from django.test import TestCase

from laws.models import Vote, Bill, KnessetProposal

just_id = lambda x: x.id
APP = 'laws'


class BillStreamTest(TestCase):
    def setUp(self):
        super(BillStreamTest, self).setUp()
        self.vote_1 = Vote.objects.create(time=datetime(2010, 12, 18),
                                          title='vote 1')
        self.vote_2 = Vote.objects.create(time=datetime(2011, 4, 4),
                                          title='vote 2')
        self.bill = Bill.objects.create(stage='1', title='bill 1', popular_name="The Bill")
        self.bill.pre_votes.add(self.vote_1)
        self.bill.first_vote = self.vote_2
        self.kp_1 = KnessetProposal.objects.create(booklet_number=2, bill=self.bill, date=datetime(2005, 1, 22))

    def teardown(self):
        super(BillStreamTest, self).tearDown()

    def testGenerate(self):
        self.bill.generate_activity_stream()
        s = Action.objects.stream_for_actor(self.bill)
        self.assertEqual(s.count(), 3)

    def tearDown(self):
        self.bill.pre_votes.all().delete()
        self.vote_1.delete()
        self.vote_2.delete()
        self.kp_1.delete()
        self.bill.delete()
