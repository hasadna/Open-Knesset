import datetime
import re
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.utils import translation
from django.conf import settings
from tagging.models import Tag,TaggedItem
from laws.models import Vote, VoteAction, Bill, Law
from mks.models import Member,Party,WeeklyPresence,Knesset
from committees.models import Committee
from agendas.models import Agenda
from knesset.sitemap import sitemaps
from django.utils import simplejson as json
from auxiliary.views import CsvView
from django.core import cache

class TagResourceTest(TestCase):

    def setUp(self):
        cache.cache.clear()
        self.tags = []
        self.tags.append(Tag.objects.create(name = 'tag1'))
        self.tags.append(Tag.objects.create(name = 'tag2'))
        self.tags.append(Tag.objects.create(name = 'tag3'))

        self.vote = Vote.objects.create(title="vote 1", time=datetime.datetime.now())
        ctype = ContentType.objects.get_for_model(Vote)
        TaggedItem._default_manager.get_or_create(tag=self.tags[0], content_type=ctype, object_id=self.vote.id)
        TaggedItem._default_manager.get_or_create(tag=self.tags[1], content_type=ctype, object_id=self.vote.id)
        self.law = Law.objects.create(title='law 1')
        self.bill = Bill.objects.create(stage='1',
                                          stage_date=datetime.date.today(),
                                          title='bill 1',
                                          law=self.law)
        self.bill2 = Bill.objects.create(stage='2',
                                          stage_date=datetime.date.today(),
                                          title='bill 2',
                                          law=self.law)
        Tag.objects.add_tag(self.bill, 'tag1')
        Tag.objects.add_tag(self.bill2, 'tag3')

    def _reverse_api(self, name, **args):
        args.update(dict(api_name='v2', resource_name='tag'))
        return reverse(name, kwargs=args)

    def test_api_tag_list(self):
        res = self.client.get(self._reverse_api('api_dispatch_list'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)['objects']
        self.assertEqual(len(res_json), 3)
        self.assertEqual(set([x['name'] for x in res_json]), set(Tag.objects.values_list('name',flat=True)))

    def test_api_tag(self):
        res = self.client.get(self._reverse_api('api_dispatch_detail', pk = self.tags[0].id))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['name'], self.tags[0].name)

    def test_api_tag_not_found(self):
        res = self.client.get(self._reverse_api('api_dispatch_detail', pk = 12345))
        self.assertEqual(res.status_code, 404)

    def test_api_tag_for_vote(self):
        res = self.client.get(self._reverse_api('tags-for-object', app_label='laws',
                                                object_type='vote', object_id=self.vote.id))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)['objects']
        self.assertEqual(len(res_json), 2)

    def test_api_related_tags(self):
        res = self.client.get(self._reverse_api('related-tags', app_label='laws',
                                                object_type='law', object_id=self.law.id, related_name='bills'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)['objects']
        self.assertEqual(len(res_json), 2)
        received_tags = set(Tag.objects.get(pk=x) for x in (res_json[0]['id'], res_json[1]['id']))
        self.assertEqual(received_tags, set([self.tags[0], self.tags[2]]))

class InternalLinksTest(TestCase):

    def setUp(self):
        Knesset.objects._current_knesset = None
        #self.vote_1 = Vote.objects.create(time=datetime.now(),title='vote 1')
        self.knesset = Knesset.objects.create(number=1,
                        start_date=datetime.date.today()-datetime.timedelta(days=100))
        self.party_1 = Party.objects.create(name='party 1', number_of_seats=4,
                                            knesset=self.knesset)
        self.vote_1 = Vote.objects.create(title="vote 1", time=datetime.datetime.now())
        self.mks = []
        self.plenum = Committee.objects.create(name='Plenum',type='plenum')
        self.voteactions = []
        self.num_mks = 4
        for i in range(self.num_mks):
            mk = Member.objects.create(name='mk %d' % i, current_party=self.party_1)
            wp = WeeklyPresence(member=mk,date=datetime.date.today(),hours=float(i))
            wp.save()
            self.mks.append(mk)
            if i<2:
                self.voteactions.append(VoteAction.objects.create(member=mk,type='for',vote=self.vote_1))
            else:
                self.voteactions.append(VoteAction.objects.create(member=mk,type='against',vote=self.vote_1))
        self.vote_1.controversy = min(self.vote_1.for_votes_count, self.vote_1.against_votes_count)
        self.vote_1.save()
        self.tags = []
        self.tags.append(Tag.objects.create(name = 'tag1'))
        self.tags.append(Tag.objects.create(name = 'tag2'))
        ctype = ContentType.objects.get_for_model(Vote)
        TaggedItem._default_manager.get_or_create(tag=self.tags[0], content_type=ctype, object_id=self.vote_1.id)
        TaggedItem._default_manager.get_or_create(tag=self.tags[1], content_type=ctype, object_id=self.vote_1.id)
        self.agenda = Agenda.objects.create(name="agenda 1 (public)", public_owner_name="owner", is_public=True)
        self.private_agenda = Agenda.objects.create(name="agenda 2 (private)", public_owner_name="owner")
        self.bill_1 = Bill.objects.create(stage='1', title='bill 1', popular_name="The Bill")
        ctype = ContentType.objects.get_for_model(Bill)
        TaggedItem._default_manager.get_or_create(tag=self.tags[0], content_type=ctype, object_id=self.bill_1.id)
        self.domain = 'http://' + Site.objects.get_current().domain

    def test_internal_links(self):
        """
        Internal links general test.
        This test reads the site, starting from the main page,
        looks for links, and makes sure all internal pages return HTTP200
        """
        from django.conf import settings
        translation.activate(settings.LANGUAGE_CODE)
        visited_links = set()

        test_pages = [reverse('main'), reverse('vote-list'),
                      reverse('bill-list'),
                      reverse('parties-members-list', kwargs={'pk': '1' })]

        redirects = [
            reverse('party-list'), reverse('member-list'),
            reverse('parties-members-index'),
        ]

        for page in test_pages:

            links_to_visit = []
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)
            visited_links.add(page)
            for link in re.findall("href=\"(.*?)\"",res.content):
                link = link.lower()
                self.failUnless(link, "There seems to be an empty link in %s (href='')" % page)
                if (link in visited_links) or (link.startswith("http")) or link.startswith("#"):
                    continue
                if link.startswith("../"):
                    link = '/' + '/'.join(link.split('/')[1:])
                elif link.startswith("./"):
                    link = link[2:]
                elif link.startswith("."):
                    link = link[1:]
                if not link.startswith("/"): # relative
                    link = "%s%s" % (page,link)

                if link.find(settings.STATIC_URL)>=0: # skip testing static files
                    continue

                links_to_visit.append(link)

            while links_to_visit:
                link = links_to_visit.pop()
                res0 = self.client.get(link)

                if link in redirects:
                    self.assertEqual(res0.status_code, 301, msg="internal redirect %s from page %s seems to be broken" % (link,page))
                else:
                    self.assertEqual(res0.status_code, 200, msg="internal link %s from page %s seems to be broken" % (link,page))
                visited_links.add(link)

        # generate a txt file report of the visited links. for debugging the test
        #visited_links = list(visited_links)
        #visited_links.sort()
        #f = open('internal_links_tested.txt','wt')
        #f.write('\n'.join(visited_links))
        #f.close()


class SiteMapTest(TestCase):

    def setUp(self):
        pass

    def test_sitemap(self):
        res = self.client.get(reverse('sitemap'))
        self.assertEqual(res.status_code, 200)
        for s in sitemaps.keys():
            res = self.client.get(reverse('sitemaps', kwargs={'section':s}))
            self.assertEqual(res.status_code, 200, 'sitemap %s returned %d' %
                             (s,res.status_code))


class CsvViewTest(TestCase):

    class TestModel(object):
        def __init__(self, value):
            self.value = value

        def squared(self):
            return self.value ** 2

    class ConcreteCsvView(CsvView):
        filename = 'test.csv'
        list_display = (("value", "value"),
                        ("squared", "squared"))

    def test_csv_view(self):
        view = self.ConcreteCsvView()
        view.model = self.TestModel
        view.queryset = [self.TestModel(2), self.TestModel(3)]
        response = view.dispatch(None)
        rows = response.content.splitlines()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1], '2,4')
        self.assertEqual(rows[2], '3,9')
