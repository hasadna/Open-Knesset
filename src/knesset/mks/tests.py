import re

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sites.models import Site
from actstream import follow,action
from actstream.models import Action
from knesset.mks.models import Member, Party, Membership, MemberAltname
from knesset.mks.views import MemberListView
from knesset.laws.models import Law,Bill,PrivateProposal,Vote,VoteAction
from knesset.committees.models import CommitteeMeeting,Committee
from knesset.utils import RequestFactory
import datetime
import feedparser
from backlinks.tests.xmlrpc import TestClientServerProxy
from xmlrpclib import Fault, loads
from urllib import urlencode
from backlinks.models import InboundBacklink
from backlinks.pingback.server import PingbackServer
from django import template
#from knesset.mks.server_urls import mock_pingback_server
from knesset.mks.mock import PINGABLE_MEMBER_ID, NON_PINGABLE_MEMBER_ID
from django.utils import simplejson as json

TRACKBACK_CONTENT_TYPE = 'application/x-www-form-urlencoded; charset=utf-8'


just_id = lambda x: x.id

class MemberViewsTest(TestCase):

    def setUp(self):
        self.party_1 = Party.objects.create(name='party 1')
        self.party_2 = Party.objects.create(name='party 2')
        self.mk_1 = Member.objects.create(name='mk_1',
                                          start_date=datetime.date(2010,1,1),
                                          current_party=self.party_1,
                                          backlinks_enabled=True)
        self.mk_2 = Member.objects.create(name='mk_2',
                                          start_date=datetime.date(2010,1,1),
                                           current_party=self.party_1,
                                           backlinks_enabled = False)
        self.jacob = User.objects.create_user('jacob', 'jacob@jacobian.org',
                                              'JKM')
        
        self.committee_1 = Committee.objects.create(name='c1')
        self.meeting_1 = self.committee_1.meetings.create(date=datetime.date.today()-datetime.timedelta(1),
                                 protocol_text='jacob:\nI am a perfectionist\nadrian:\nI have a deadline')
        self.meeting_2 = self.committee_1.meetings.create(date=datetime.date.today()-datetime.timedelta(2),
                                 protocol_text='adrian:\nYou are a perfectionist\njacob:\nYou have a deadline')
        self.law = Law.objects.create(title='law 1')
        self.pp = PrivateProposal.objects.create(title='private proposal 1', date=datetime.date.today()-datetime.timedelta(3))
        self.pp.proposers.add(self.mk_1)
        self.bill_1 = Bill.objects.create(stage='1', title='bill 1', law=self.law)
        self.bill_1.proposals.add(self.pp)
        self.bill_1.proposers.add(self.mk_1)
        self.meeting_1.mks_attended.add(self.mk_1)
        self.meeting_1.save()
        self.meeting_2.mks_attended.add(self.mk_1)
        self.meeting_2.save()
        self.vote = Vote.objects.create(title='vote 1',time=datetime.datetime.now())
        self.vote_action = VoteAction.objects.create(member=self.mk_1, vote=self.vote, type='for')
        self.domain = 'http://' + Site.objects.get_current().domain

    def testMemberList(self):
        res = self.client.get(reverse('member-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'mks/member_list_with_bars.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list), 
                         [ self.mk_1.id, self.mk_2.id, ])

    def testMemberDetail(self):

        res = self.client.get(reverse('member-detail',
                                      args=[self.mk_1.id]))
        self.assertTemplateUsed(res,
                                'mks/member_detail.html')
        self.assertEqual(res.context['object'].id, self.mk_1.id)

    def testMemberSearch(self):
        res = self.client.get(reverse('member-handler'),
                                      {'q': 'mk_'},
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        p = json.loads(res.content)
        self.assertEqual(set(map(lambda x: x['id'], p)), set((self.mk_1.id, self.mk_2.id)))

        res = self.client.get(reverse('member-handler'),
                                      {'q': 'mk_1'},
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        p = json.loads(res.content)
        self.assertEqual(map(lambda x:x['id'], p), [self.mk_1.id])

    def testPartyList(self):
        res = self.client.get(reverse('party-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'mks/party_list.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list), 
                         [ self.party_1.id, self.party_2.id, ])

    def testPartyDetail(self):
        res = self.client.get(reverse('party-detail', 
                              args=[self.party_1.id]))
        self.assertTemplateUsed(res, 'mks/party_detail.html')
        self.assertEqual(res.context['object'].id, self.party_1.id)

    def testPartySearch(self):
        res = self.client.get(reverse('party-handler'),
                                      {'q': 'party'},
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        p = json.loads(res.content)
        self.assertEqual(set(map(lambda x: x['id'], p)), set((self.party_1.id,self.party_2.id)))

        res = self.client.get(reverse('party-handler'),
                                      {'q': 'party%201'},
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        p = json.loads(res.content)
        self.assertEqual(map(lambda x:x['id'], p), [self.party_1.id])

    def testMemberDetailsContext(self):

        # test anonymous user
        mk_1_url = self.mk_1.get_absolute_url()
        res = self.client.get(mk_1_url)
        self.assertFalse(res.context['watched_member'])
        # test autherized user
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.get(mk_1_url)
        self.assertFalse(res.context['watched_member'])
        # test autherized user that follows
        follow(self.jacob, self.mk_1)
        res = self.client.get(mk_1_url)
        self.assertTrue(res.context['watched_member'])

    def testMemberActivityFeed(self):
        res = self.client.get(reverse('member-activity-feed', 
                                      args=[self.mk_1.id]))
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        # self.assertEqual(len(parsed['entries']),4)
        self.assertEqual(parsed['entries'][0]['link'], self.domain + 
                self.vote.get_absolute_url())
        self.assertEqual(parsed['entries'][1]['link'], self.domain + 
                self.meeting_1.get_absolute_url())
        self.assertEqual(parsed['entries'][2]['link'], self.domain + 
                self.meeting_2.get_absolute_url())
        self.assertEqual(parsed['entries'][3]['link'], self.domain +
                self.bill_1.get_absolute_url())

    def testMemberActivityFeedWithVerbProposed(self):
        res = self.client.get(reverse('member-activity-feed', 
                                      kwargs={'object_id': self.mk_1.id}),{'verbs':'proposed'})
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        self.assertEqual(len(parsed['entries']),1)

        res = self.client.get(reverse('member-activity-feed', 
                                      kwargs={'object_id': self.mk_2.id}),{'verbs':'proposed'})
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        self.assertEqual(len(parsed['entries']),0)

    def testMemberActivityFeedWithVerbAttended(self):
        res = self.client.get(reverse('member-activity-feed', 
                                      kwargs={'object_id': self.mk_1.id}),{'verbs':'attended'})
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        self.assertEqual(len(parsed['entries']),2)

        res = self.client.get(reverse('member-activity-feed', 
                                      kwargs={'object_id': self.mk_2.id}),{'verbs':'attended'})
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        self.assertEqual(len(parsed['entries']),0)

    def testMemberActivityFeedWithVerbJoined(self):
        res = self.client.get(reverse('member-activity-feed', 
                                      kwargs={'object_id': self.mk_1.id}),{'verbs':'joined'})
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        self.assertEqual(len(parsed['entries']),0)
    

    def testMemberActivityFeedWithVerbPosted(self):
        res = self.client.get(reverse('member-activity-feed',
                                      kwargs={'object_id': self.mk_1.id}),{'verbs':'posted'})
        self.assertEqual(res.status_code,200)
        parsed = feedparser.parse(res.content)
        self.assertEqual(len(parsed['entries']),0)
    
    def testPartyAPI(self):
        res = self.client.get(reverse('party-handler')) #, kwargs={'object_id': self.mk_1.id}),{'verbs':'posted'})
        self.assertEqual(res.status_code,200)
        parties = json.loads(res.content)
        self.assertEqual(map(lambda x:x['id'], parties), [self.party_1.id, self.party_2.id])
    

    def tearDown(self):
        self.party_1.delete()
        self.party_2.delete()
        self.mk_1.delete()
        self.mk_2.delete()
        self.jacob.delete()
        
class MemberBacklinksViewsTest(TestCase):
    urls = 'knesset.mks.server_urls'

    def setUp(self):
        self.party_1 = Party.objects.create(name='party 1')
        self.party_2 = Party.objects.create(name='party 2')
        self.mk_1 = Member.objects.create(name='mk_1',
                                          start_date=datetime.date(2010,1,1),
                                          current_party=self.party_1,
                                          backlinks_enabled=True)
        self.mk_2 = Member.objects.create(name='mk_2',
                                          start_date=datetime.date(2010,1,1),
                                           current_party=self.party_1,
                                           backlinks_enabled = False)
        self.jacob = User.objects.create_user('jacob', 'jacob@jacobian.org',
                                              'JKM')
        
        self.mk_1.save()
        self.mk_2.save()

        self.committee_1 = Committee.objects.create(name='c1')
        self.meeting_1 = self.committee_1.meetings.create(date=datetime.date.today()-datetime.timedelta(1),
                                 protocol_text='jacob:\nI am a perfectionist\nadrian:\nI have a deadline')
        self.meeting_2 = self.committee_1.meetings.create(date=datetime.date.today()-datetime.timedelta(2),
                                 protocol_text='adrian:\nYou are a perfectionist\njacob:\nYou have a deadline')
        self.law = Law.objects.create(title='law 1')
        self.pp = PrivateProposal.objects.create(title='private proposal 1', date=datetime.date.today()-datetime.timedelta(3))
        self.pp.proposers.add(self.mk_1)
        self.bill_1 = Bill.objects.create(stage='1', title='bill 1', law=self.law)
        self.bill_1.proposals.add(self.pp)
        self.bill_1.proposers.add(self.mk_1)
        self.meeting_1.mks_attended.add(self.mk_1)
        self.meeting_1.save()
        self.meeting_2.mks_attended.add(self.mk_1)
        self.meeting_2.save()
        self.vote = Vote.objects.create(title='vote 1',time=datetime.datetime.now())
        self.vote_action = VoteAction.objects.create(member=self.mk_1, vote=self.vote, type='for')
        
        self.client = Client(SERVER_NAME='example.com')
        self.xmlrpc_client = TestClientServerProxy('/pingback/')
        self.PINGABLE_MEMBER_ID = str(self.mk_1.id)
        self.NON_PINGABLE_MEMBER_ID = str(self.mk_2.id)
        
    def trackbackPOSTRequest(self, path, params):
        return self.client.post(path, urlencode(params), content_type=TRACKBACK_CONTENT_TYPE)

    def assertTrackBackErrorResponse(self, response, msg):
        if response.content.find('<error>1</error>') == -1:
            raise self.failureException, msg
    
    '''    
    def testTrackBackRDFTemplateTag(self):
        t = template.Template("{% load trackback_tags %}{% trackback_rdf object_url object_title trackback_url True %}")
        c = template.Context({'trackback_url': '/trackback/member/'+self.PINGABLE_MEMBER_ID+'/',
                              'object_url': self.pingableTargetUrl,
                              'object_title': 'Pingable Test Entry'})
        rendered = t.render(c)
        link_re = re.compile(r'dc:identifier="(?P<link>[^"]+)"')
        match = link_re.search(rendered)
        self.assertTrue(bool(match), 'TrackBack RDF not rendered')
        self.assertEquals(match.groups('link')[0], self.pingableTargetUrl,
                          'TrackBack RDF did not contain a valid target URI')
        ping_re = re.compile(r'trackback:ping="(?P<link>[^"]+)"')
        match = ping_re.search(rendered)
        self.assertTrue(bool(match), 'TrackBack RDF not rendered')
        self.assertEquals(match.groups('link')[0], '/trackback/member/'+self.PINGABLE_MEMBER_ID+'/',
                          'TrackBack RDF did not contain a TrackBack server URI')

    '''    
    def testPingNonLinkingSourceURI(self):
        self.assertRaises(Fault,
                          self.xmlrpc_client.pingback.ping,
                          'http://example.com/bad-source-document/',
                          'http://example.com/member/'+PINGABLE_MEMBER_ID+'/')
        
        try:
            self.xmlrpc_client.pingback.ping('http://example.com/bad-source-document/',
                                             'http://example.com/member/'+PINGABLE_MEMBER_ID+'/')
        except Fault, f:
            self.assertEquals(f.faultCode,
                              17,
                             'Server did not return "source URI does not link" response')
    def testDisallowedMethod(self):
        response = self.client.get('/pingback/')
        self.assertEquals(response.status_code,
                          405,
                          'Server returned incorrect status code for disallowed HTTP method')

    def testNonExistentRPCMethod(self):
        self.assertRaises(Fault, self.xmlrpc_client.foo)


    def testBadPostData(self):
        post_data = urlencode({'sourceURI': 'http://example.com/good-source-document/',
                               'targetURI': 'http://example.com/member/'+PINGABLE_MEMBER_ID+'/'})
        response = self.client.post('/pingback/', post_data, TRACKBACK_CONTENT_TYPE)
        self.assertRaises(Fault,
                          loads,
                          response.content)

    def testPingNonExistentTargetURI(self):
        self.assertRaises(Fault,
                          self.xmlrpc_client.pingback.ping,
                          'http://example.com/member/non-existent-resource/',
                          'http://example.com/member/non-existent-resource')
        try:
            self.xmlrpc_client.pingback.ping('http://example.com/member/non-existent-resource/',
                                             'http://example.com/member/non-existent-resource')
        except Fault, f:
            self.assertEquals(f.faultCode,
                              32,
                              'Server did not return "target does not exist" error')
        
        
    def testPingAlreadyRegistered(self):
        self.xmlrpc_client.pingback.ping('http://example.com/another-good-source-document/',
                                             'http://example.com/member/'+PINGABLE_MEMBER_ID+'/')
        self.assertRaises(Fault,
                          self.xmlrpc_client.pingback.ping,
                          'http://example.com/another-good-source-document/',
                          'http://example.com/member/'+PINGABLE_MEMBER_ID+'/')

        try:
            self.xmlrpc_client.pingback.ping('http://example.com/another-good-source-document/',
                                             'http://example.com/member/'+PINGABLE_MEMBER_ID+'/')
        except Fault, f:
            self.assertEqual(f.faultCode,
                             48,
                             'Server did not return "ping already registered" error')

    def testPingbackLinkTemplateTag(self):
        t = template.Template("{% load pingback_tags %}{% pingback_link pingback_path %}")
        c = template.Context({'pingback_path': '/pingback/'})
        rendered = t.render(c)
        link_re = re.compile(r'<link rel="pingback" href="([^"]+)" ?/?>')
        match = link_re.search(rendered)
        self.assertTrue(bool(match), 'Pingback link tag did not render')
        self.assertEquals(match.groups(0)[0], 'http://example.com/pingback/',
                          'Pingback link tag rendered incorrectly')
                          
    def testPingNonPingableTargetURI(self):
        self.assertRaises(Fault,
                          self.xmlrpc_client.pingback.ping,
                          'http://example.com/member/non-existent-resource/',
                          'http://example.com/member/'+str(self.NON_PINGABLE_MEMBER_ID)+'/')
        try:
            self.xmlrpc_client.pingback.ping('http://example.com/member/non-existent-resource/',
                                             'http://example.com/member/'+str(self.NON_PINGABLE_MEMBER_ID)+'/')
        except Fault, f:
            self.assertEquals(f.faultCode, 
                              33,
                              'Server did not return "target not pingable" error')
          
    def testPingSourceURILinks(self):
        r = self.xmlrpc_client.pingback.ping('http://example.com/good-source-document/',
                                             'http://example.com/member/'+self.PINGABLE_MEMBER_ID+'/')
        
        self.assertEquals(r,
                          "Ping from http://example.com/good-source-document/ to http://example.com/member/1/ registered",
                          "Failed registering ping")
        
        registered_ping = InboundBacklink.objects.get(source_url='http://example.com/good-source-document/',
                                                      target_url='http://example.com/member/'+self.PINGABLE_MEMBER_ID+'/')
        self.assertEquals(str(registered_ping.target_object.id), 
                              PINGABLE_MEMBER_ID,
                              'Server did not return "target not pingable" error')
        
    def testDisallowedTrackbackMethod(self):
        response = self.client.get('/trackback/member/'+PINGABLE_MEMBER_ID+'/')
        self.assertEquals(response.status_code,
                          405,
                          'Server returned incorrect status code for disallowed HTTP method')

    def testPingNoURLParameter(self):
        params = {'title': 'Example', 'excerpt': 'Example'}
        response = self.trackbackPOSTRequest('/trackback/member/'+self.PINGABLE_MEMBER_ID+'/',
                                             params)
        self.assertTrackBackErrorResponse(response,
                                          'Server did not return error response'
                                          'for ping with no URL parameter')
                                          
    def testPingBadURLParameter(self):
        params = {'url': 'bad url'}
        response = self.trackbackPOSTRequest('http://example.com/trackback/member/'+self.PINGABLE_MEMBER_ID+'/',
                                             params)
        self.assertTrackBackErrorResponse(response,
                                          'Server did not return error response for ping with bad URL parameter')
                                          
    def testPingNonExistentTarget(self):
        params = {'url': 'http://example.com/good-source-document/'}
        response = self.trackbackPOSTRequest('/trackback/member/5000/',
                                             params)
        self.assertTrackBackErrorResponse(response,
                                          'Server did not return error response for ping against non-existent resource')
                                          
    def testPingNonPingableTarget(self):
        params = {'url': 'http://example.com/member/'+PINGABLE_MEMBER_ID+'/'}
        response = self.trackbackPOSTRequest('/trackback/member/'+self.NON_PINGABLE_MEMBER_ID+'/',
                                             params)
        self.assertTrackBackErrorResponse(response,
                                          'Server did not return error response for ping against non-pingable resource')

    def testPingSuccess(self):
        title = 'Backlinks Test - Test Good Source Document'
        excerpt = 'This is a summary of the good source document'
        params = {'url': 'http://example.com/good-source-document/', 'title': title, 'excerpt': excerpt}
        track_target = '/trackback/member/'+self.PINGABLE_MEMBER_ID+'/'
        response = self.trackbackPOSTRequest(track_target,
                                             params)
        self.assertTrue(response.content.find('<error>0</error>') > -1,
                        'Server did not return success response for a valid ping request')
        registered_ping = InboundBacklink.objects.get(source_url='http://example.com/good-source-document/',
                                                      target_url='http://example.com'+self.mk_1.get_absolute_url())
        self.assertEquals(registered_ping.title,
                          title,
                          'Server did not use title from ping request when registering')
        self.assertEquals(registered_ping.excerpt,
                          excerpt,
                          'Server did not use excerpt from ping request when registering')

    def tearDown(self):
        self.party_1.delete()
        self.party_2.delete()
        self.mk_1.delete()
        self.mk_2.delete()
        self.jacob.delete()


class MemberModelsTests(TestCase):

    def testNames(self):
        m=Member(name='test member')
        self.assertEqual(m.names, ['test member'])
        m.save()
        MemberAltname(member=m,name='test2').save()
        self.assertEqual(m.names, ['test member','test2'])

from agendas.models import Agenda, AgendaVote

class MKAgendasTest(TestCase):

    def setUp(self):
        self.party_1 = Party.objects.create(name='party 1', number_of_seats=1)
        self.mk_1 = Member.objects.create(name='mk_1',
                                          start_date=datetime.date(2010,1,1),
                                          current_party=self.party_1)

        self.mk_2 = Member.objects.create(name='mk_2',
                                          start_date=datetime.date(2010,1,1),
                                          current_party=self.party_1)

        self.mk_3 = Member.objects.create(name='mk_3',
                                          start_date=datetime.date(2010,1,1),
                                          current_party=self.party_1)

        self.agenda_1 = Agenda.objects.create(name='agenda 1',
                                              description='a bloody good agenda 1',
                                              public_owner_name='Dr. Jacob',
                                              is_public=True)
        self.agenda_2 = Agenda.objects.create(name='agenda 2',
                                              description='a bloody good agenda 2',
                                              public_owner_name='Greenpeace',
                                              is_public=True)
        self.agenda_3 = Agenda.objects.create(name='agenda 3',
                                              description='a bloody good agenda 3',
                                              public_owner_name='Hidden One',
                                              is_public=False)
        self.vote_1 = Vote.objects.create(title='vote 1',time=datetime.datetime.now())
        self.vote_2 = Vote.objects.create(title='vote 2',time=datetime.datetime.now())
        self.voteactions = [ VoteAction.objects.create(vote=self.vote_1,
                                member=self.mk_1, type='for'),
                             VoteAction.objects.create(vote=self.vote_2,
                                member=self.mk_1, type='for'),
                             VoteAction.objects.create(vote=self.vote_1,
                                member=self.mk_2, type='against'),
                             VoteAction.objects.create(vote=self.vote_2,
                                member=self.mk_2, type='against'),
                             ]
        self.agendavotes = [AgendaVote.objects.create(agenda=self.agenda_1,
                                                      vote=self.vote_1,
                                                      score=-1,
                                                      reasoning="there's got to be a reason 1"),
                            AgendaVote.objects.create(agenda=self.agenda_2,
                                                      vote=self.vote_2,
                                                      score=0.5,
                                                      reasoning="there's got to be a reason 2"),
                            AgendaVote.objects.create(agenda=self.agenda_1,
                                                      vote=self.vote_2,
                                                      score=0.5,
                                                      reasoning="there's got to be a reason 3"),
                            ]

        self.domain = 'http://' + Site.objects.get_current().domain

    def testMemberValues(self):
        agenda_values1 = self.mk_1.get_agendas_values()
        self.assertEqual(len(agenda_values1), 2)
        agenda_values2 = self.mk_2.get_agendas_values()
        self.assertEqual(len(agenda_values2), 2)
        self.assertEqual(agenda_values1,
                {1: {'rank': 2, 'score': -33.33}, 
                 2: {'rank': 1, 'score': 100.0}})
        self.assertEqual(agenda_values2,
                {1: {'rank': 1, 'score': 33.33},
                 2: {'rank': 2, 'score': -100.0}})
        agenda_values = self.mk_3.get_agendas_values()
        self.assertFalse(agenda_values)

    def testAPIv2(self):
        res = self.client.get('/api/v2/member/%s/?format=json' % self.mk_1.id)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['name'], 'mk_1')
        self.assertEqual(data['party_name'], self.party_1.name)
        self.assertEqual(data['party_url'], self.party_1.get_absolute_url())
        agendas_uri = data['agendas_uri']
        expected_agendas_uri = '/api/v2/member-agendas/%s/' % self.mk_1.id
        self.assertEqual(agendas_uri, expected_agendas_uri, "Wrong agendas URI returned for member")
        res2 = self.client.get(expected_agendas_uri+'?format=json')
        agendas = json.loads(res2.content)
        self.assertEqual(agendas['agendas'], [
            {'id': 1, 'owner': 'Dr. Jacob', 'absolute_url': '/agenda/1/', 
             'score': -33.33, 'name': 'agenda 1', 'rank': 2,
             'min': -33.33, 'max': 33.33,
             'party_min': -33.33, 'party_max': 33.33,
            },
            {'id': 2, 'owner': 'Greenpeace', 'absolute_url': '/agenda/2/', 
             'score': 100.0, 'name': 'agenda 2', 'rank': 1,
             'min': -100.0, 'max': 100.0,
             'party_min': -100.0, 'party_max': 100.0,
            }])

    def tearDown(self):
        for av in self.agendavotes:
            av.delete()
        for va in self.voteactions:
            va.delete()
        self.vote_1.delete()
        self.vote_2.delete()
        self.mk_1.delete()
        self.mk_2.delete()
        self.party_1.delete()
        self.agenda_1.delete()
        self.agenda_2.delete()
        self.agenda_3.delete()
