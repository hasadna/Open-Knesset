# encoding: utf-8
#

import json
from datetime import date, timedelta, datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from tagging.models import Tag

from agendas.models import Agenda, AgendaVote, AgendaBill
from laws.models import Vote, Bill, KnessetProposal, Law
from mks.models import Knesset, Party, Member

just_id = lambda x: x.id
APP = 'laws'

class APIv2Test(TestCase):
    def setUp(self):
        super(APIv2Test, self).setUp()
        d = date.today()
        self.knesset = Knesset.objects.create(
                number=1,
                start_date=d - timedelta(10))
        self.url_prefix = '/api/v2'
        self.vote_1 = Vote.objects.create(time=datetime.now(),
                                          title='vote 1')
        self.vote_2 = Vote.objects.create(time=datetime.now(),
                                          title='vote 2')
        self.party_1 = Party.objects.create(name='party 1')
        self.mk_1 = Member.objects.create(name='mk 2',
                                          current_party=self.party_1)
        # Membership.objects.create(member=self.mk_1, party=self.party_1)
        self.bill_1 = Bill.objects.create(stage='1', title='bill 1',
                                          popular_name="The Bill")
        self.bill_1.proposers.add(self.mk_1)
        self.bill_2 = Bill.objects.create(stage='2', title='bill 2',
                                          popular_name="Another Bill")
        self.kp_1 = KnessetProposal.objects.create(booklet_number=2,
                                                   bill=self.bill_1,
                                                   date=date.today())
        self.law_1 = Law.objects.create(title='law 1')
        self.tag_1 = Tag.objects.create(name='tag1')

        self.agenda_1 = Agenda.objects.create(name='agenda 1',
                                              public_owner_name='owner name')
        self.agenda_vote = AgendaVote.objects.create(agenda=self.agenda_1,
                                                     vote=self.vote_1)

        self.agenda_2 = Agenda.objects.create(name='agenda 2',
                                              public_owner_name='owner name 2')
        self.agenda_bill_1 = AgendaBill.objects.create(agenda=self.agenda_2,
                                                       bill=self.bill_1)

        self.agenda_3 = Agenda.objects.create(name='agenda 3',
                                              public_owner_name='owner name 3', is_public=True)
        self.agenda_bill_2 = AgendaBill.objects.create(agenda=self.agenda_3,
                                                       bill=self.bill_1)

        self.agenda_4 = Agenda.objects.create(name='agenda 4',
                                              public_owner_name='owner name 4', is_public=False)
        self.agenda_bill_3 = AgendaBill.objects.create(agenda=self.agenda_4,
                                                       bill=self.bill_1)

        self.adrian = User.objects.create_user('adrian', 'adrian@example.com',
                                               'ADRIAN')
        self.adrian.agendas.add(self.agenda_2)

    def teardown(self):
        super(APIv2Test, self).tearDown()

    def test_law_resource(self):
        uri = '%s/law/%s/' % (self.url_prefix, self.law_1.id)
        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['resource_uri'], uri)
        self.assertEqual(int(data['id']), self.law_1.id)
        self.assertEqual(data['title'], "law 1")

    def test_bill_agenda_logged(self):
        p = self.adrian.profiles.get()
        loggedin = self.client.login(username='adrian', password='ADRIAN')
        self.assertTrue(loggedin)

        uri = '%s/bill/%s/' % (self.url_prefix, self.bill_1.id)

        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)

        agendas = data['agendas']

        self.assertEqual(len(agendas['agenda_list']), 2)
        self.assertEqual(agendas['agenda_list'][0]['name'], self.agenda_2.name)
        self.assertEqual(agendas['agenda_list'][0]['public_owner_name'], self.agenda_2.public_owner_name)
        self.assertEqual(agendas['agenda_list'][0]['resource_uri'],
                         '%s/agenda/%s/' % (self.url_prefix, self.agenda_2.id))

    def test_bill_agenda_unlogged(self):
        uri = '%s/bill/%s/' % (self.url_prefix, self.bill_1.id)

        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)

        agendas = data['agendas']
        print data

        self.assertEqual(len(agendas['agenda_list']), 1)

    def test_bill_resource(self):
        uri = '%s/bill/%s/' % (self.url_prefix, self.bill_1.id)
        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['resource_uri'], uri)
        self.assertEqual(int(data['id']), self.bill_1.id)
        self.assertEqual(data['title'], "bill 1")

    def test_vote_resource(self):
        uri = '%s/vote/%s/' % (self.url_prefix, self.vote_1.id)
        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['resource_uri'], uri)
        self.assertEqual(int(data['id']), self.vote_1.id)
        self.assertEqual(data['title'], "vote 1")
        self.assertEqual(data["agendas"][0]['name'], "agenda 1")

    def test_vote_exports_does_not_break_on_missing_date_from_filter(self):
        uri = '/api/v2/vote/?vtype=second-call&order=time&from_date=&to_date=2016-02-13'
        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)

    def test_bill_list(self):
        uri = reverse('api_dispatch_list', kwargs={'resource_name': 'bill',
                                                   'api_name': 'v2'})
        res = self.client.get(uri, format='json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['meta']['total_count'], 2)
        self.assertEqual(len(data['objects']), 2)

    def test_bill_list_for_proposer(self):
        uri = reverse('api_dispatch_list', kwargs={'resource_name': 'bill',
                                                   'api_name': 'v2'})
        res = self.client.get(uri, dict(proposer=self.mk_1.id, format='json'))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['meta']['total_count'], 1)
        self.assertEqual(len(data['objects']), 1)

    def tearDown(self):
        self.vote_1.delete()
        self.vote_2.delete()
        self.bill_1.delete()
        self.bill_2.delete()
        self.agenda_1.delete()
        self.agenda_2.delete()
        self.agenda_3.delete()
        self.agenda_4.delete()
        self.law_1.delete()
        self.mk_1.delete()
        self.party_1.delete()
        self.tag_1.delete()
        self.adrian.delete()