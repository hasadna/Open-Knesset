import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Group, Permission
from tagging.models import Tag, TaggedItem
from laws.models import Vote, VoteAction, Bill, Law
from mks.models import Member, Party, Knesset
from agendas.models import Agenda
from committees.models import Committee
from events.models import Event
from django.utils import simplejson as json
from django.core import cache
from voting.models import Vote as UserVote

class TestAPIV2(TestCase):
    """
    General tests for the API V2, not specific to any app (app-specific tests
    are located in the app directories).
    """

    def setUp(self):
        pass

    def test_empty_cache_bug(self):
        """ Tastypie has a bug when the cache returns None. this test verifies
        that our fork of Tastypie doesn't have it. This test should be run with
        DummyCache settings"""
        res = self.client.get('/api/v2/vote/?format=json')
        self.assertEqual(res.status_code, 200)


class ApiViewsTest(TestCase):

    def setUp(self):
        cache.cache.clear()
        Knesset.objects._current_knesset=None
        #self.vote_1 = Vote.objects.create(time=datetime.now(),title='vote 1')
        self.knesset = Knesset.objects.create(number=1,
                start_date=datetime.date.today()-datetime.timedelta(days=30))

        self.party_1 = Party.objects.create(name='party 1', knesset=self.knesset)
        self.vote_1 = Vote.objects.create(title="vote 1", time=datetime.datetime.now())
        self.mks = []
        self.voteactions = []
        self.num_mks = 30
        for i in range(self.num_mks):
            mk = Member.objects.create(name='mk %d' % i,current_party=self.party_1)
            self.mks.append(mk)
            self.voteactions.append(VoteAction.objects.create(member=mk,type='for',vote=self.vote_1))
        self.tags = []
        self.tags.append(Tag.objects.create(name = 'tag1'))
        self.tags.append(Tag.objects.create(name = 'tag2'))
        ctype = ContentType.objects.get_for_model(Vote)
        TaggedItem._default_manager.get_or_create(tag=self.tags[0], content_type=ctype, object_id=self.vote_1.id)
        TaggedItem._default_manager.get_or_create(tag=self.tags[1], content_type=ctype, object_id=self.vote_1.id)
        self.agenda = Agenda.objects.create(name="agenda 1 (public)", public_owner_name="owner", is_public=True)
        self.private_agenda = Agenda.objects.create(name="agenda 2 (private)", public_owner_name="owner")
        self.law_1 = Law.objects.create(title='law 1')
        self.bill_1 = Bill.objects.create(stage='1',
                                          stage_date=datetime.date.today(),
                                          title='bill 1',
                                          law=self.law_1)
        self.bill_1.proposers.add(self.mks[0])
        Tag.objects.add_tag(self.bill_1, 'tag1')
        self.bill_2 = Bill.objects.create(stage='-1',
                                          stage_date=datetime.date.today()-datetime.timedelta(10),
                                          title='bill 2',
                                          law=self.law_1)
        self.bill_2.proposers.add(self.mks[1])
        self.bill_2.proposers.add(self.mks[2])
        self.bill_3 = Bill.objects.create(stage='2',
                                          stage_date=datetime.date.today()-datetime.timedelta(10),
                                          title='bill 3',
                                          law=self.law_1)
        self.bill_4 = Bill.objects.create(stage='2',
                                          stage_date=datetime.date.today()-datetime.timedelta(10),
                                          title='bill 4',
                                          law=self.law_1)

        # add user votings for the bills
        self.users = []
        for i in xrange(4):
            self.users.append(User.objects.create_user('user%d'%i, 'user%d@example.com'%i, 'test'))

        for i in xrange(4):
            UserVote.objects.record_vote(self.users[i], self.bill_1, +1)
        for i in xrange(3):
            UserVote.objects.record_vote(self.users[i], self.bill_2, +1)
        for i in xrange(4):
            UserVote.objects.record_vote(self.users[i], self.bill_3, +1 if i%2 == 0 else -1)

    def test_api_member_list(self):
        res = self.client.get(reverse('member-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), self.num_mks)

    def test_api_member(self):
        res = self.client.get(reverse('member-handler', args=[self.mks[0].id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['name'], self.mks[0].name)

    def test_api_member_not_found(self):
        res = self.client.get(reverse('member-handler', args=[123456]))
        self.assertEqual(res.status_code, 404)

    def test_api_party_list(self):
        res = self.client.get(reverse('party-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 1)
        self.assertEqual(res_json[0]["name"],self.party_1.name)

    def test_api_party(self):
        res = self.client.get(reverse('party-handler', args=[self.party_1.id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json["name"],self.party_1.name)

    def test_api_party_not_found(self):
        res = self.client.get(reverse('party-handler', args=[123456]))
        self.assertEqual(res.status_code, 404)

    def test_api_vote_list(self):
        res = self.client.get(reverse('vote-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 1)
        self.assertEqual(len(res_json[0]['for_votes']), self.num_mks)

    def test_api_vote(self):
        res = self.client.get(reverse('vote-handler', args=[self.vote_1.id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json['for_votes']), self.num_mks)

    def test_api_vote_not_found(self):
        res = self.client.get(reverse('vote-handler', args=[123456]))
        self.assertEqual(res.status_code, 404)

    def test_api_bill(self):
        res = self.client.get(reverse('bill-handler', args=[self.bill_1.id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['bill_title'], u"%s, %s" % (self.bill_1.law.title, self.bill_1.title))

    def test_api_bill_list(self):
        res = self.client.get(reverse('bill-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 4)
        self.assertEqual(len(res_json[0]['proposing_mks']), 1)

    def test_api_bill_list_with_days_back(self):
        res = self.client.get('%s?days_back=2' % reverse('bill-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 1)
        self.assertEqual(len(res_json[0]['proposing_mks']), 1)

    def test_api_bill_list_popular_without_type(self):
        res = self.client.get(reverse('popular-bills-handler',kwargs={'popular': True}))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 3)
        self.assertEqual(set([res_json[0]['bill_title'], res_json[1]['bill_title']]),
                         set([u"%s, %s" % (self.bill_1.law.title, self.bill_1.title),
                             u"%s, %s" % (self.bill_3.law.title, self.bill_3.title)]))
        self.assertEqual(res_json[2]['bill_title'], u"%s, %s" % (self.bill_2.law.title, self.bill_2.title))

    def test_api_bill_list_popular_with_type(self):
        res = self.client.get('%s?type=positive' % reverse('popular-bills-handler',kwargs={'popular': True}))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 2)
        self.assertEqual(res_json[0]['bill_title'], u"%s, %s" % (self.bill_1.law.title, self.bill_1.title))
        self.assertEqual(res_json[1]['bill_title'], u"%s, %s" % (self.bill_2.law.title, self.bill_2.title))

        res = self.client.get('%s?type=negative' % reverse('popular-bills-handler',kwargs={'popular': True}))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 0)

    def test_api_tag_list(self):
        res = self.client.get(reverse('tag-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 2)
        self.assertEqual(set([x['name'] for x in res_json]), set(Tag.objects.values_list('name',flat=True)))

    def test_api_tag(self):
        res = self.client.get(reverse('tag-handler', args=[self.tags[0].id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['name'], self.tags[0].name)

    def test_api_tag_not_found(self):
        res = self.client.get(reverse('tag-handler', args=[123456]))
        self.assertEqual(res.status_code, 404)

    def test_api_tag_for_vote(self):
        res = self.client.get(reverse('tag-handler',
                                      args=['laws', 'vote',
                                            self.vote_1.id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 2)

    def test_api_agenda_list(self):
        res = self.client.get(reverse('agenda-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 1)

    def test_api_agenda(self):
        res = self.client.get(reverse('agenda-handler', args=[self.agenda.id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['name'], self.agenda.name)

    def test_api_agenda_not_found(self):
        res = self.client.get(reverse('agenda-handler', args=[123456]))
        self.assertEqual(res.status_code, 404)

    def test_api_agenda_private(self):
        res = self.client.get(reverse('agenda-handler', args=[self.private_agenda.id]))
        self.assertEqual(res.status_code, 404)


    def tearDown(self):
        for i in range(self.num_mks):
            self.mks[i].delete()
            self.voteactions[i].delete()
        for t in self.tags:
            t.delete()
        self.agenda.delete()
        self.private_agenda.delete()

class MeetingApiTest(TestCase):

    def setUp(self):
        self.knesset = Knesset.objects.create(number=1,
                            start_date=datetime.date.today()-datetime.timedelta(days=1))
        self.committee_1 = Committee.objects.create(name='c1')
        self.committee_2 = Committee.objects.create(name='c2')
        self.meeting_1 = self.committee_1.meetings.create(date=datetime.datetime.now(),
                                 protocol_text='''jacob:
I am a perfectionist
adrian:
I have a deadline''')
        self.meeting_1.create_protocol_parts()
        self.meeting_2 = self.committee_1.meetings.create(date=datetime.datetime.now(),
                                                         protocol_text='m2')
        self.meeting_2.create_protocol_parts()
        self.jacob = User.objects.create_user('jacob', 'jacob@example.com',
                                              'JKM')
        self.adrian = User.objects.create_user('adrian', 'adrian@example.com',
                                              'ADRIAN')
        (self.group, created) = Group.objects.get_or_create(name='Valid Email')
        if created:
            self.group.save()
        self.group.permissions.add(Permission.objects.get(name='Can add annotation'))
        self.jacob.groups.add(self.group)

        ct = ContentType.objects.get_for_model(Tag)
        self.adrian.user_permissions.add(Permission.objects.get(codename='add_tag', content_type=ct))

        self.bill_1 = Bill.objects.create(stage='1', title='bill 1')
        self.mk_1 = Member.objects.create(name='mk 1')
        self.topic = self.committee_1.topic_set.create(creator=self.jacob,
                                                title="hello", description="hello world")
        self.tag_1 = Tag.objects.create(name='tag1')

    def testCommitteeMeeting(self):
        res = self.client.get(reverse('committee-meeting-handler', args=[self.meeting_1.id]))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['committee']['name'], self.committee_1.name)
        self.assertEqual(res_json['committee']['url'], self.committee_1.get_absolute_url())
        self.assertEqual(res_json['url'], self.meeting_1.get_absolute_url())

class EventTest(TestCase):
    def setUp(self):
        self.ev1 = Event.objects.create(when=datetime.datetime.now()-datetime.timedelta(1), what="ev1")
        self.ev2 = Event.objects.create(when=datetime.datetime.now()+datetime.timedelta(1), what="ev2")

    def testEventlList(self):
        res = self.client.get(reverse('event-handler'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(len(res_json), 1)
        self.assertEqual(res_json[0]['what'], 'ev2')

