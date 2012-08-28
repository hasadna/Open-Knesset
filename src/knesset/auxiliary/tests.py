import datetime
import re
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.utils import translation
from django.conf import settings
from tagging.models import Tag,TaggedItem
from knesset.laws.models import Vote, VoteAction, Bill
from knesset.mks.models import Member,Party,WeeklyPresence
from knesset.agendas.models import Agenda
from knesset.sitemap import sitemaps
from django.utils import simplejson as json

class InternalLinksTest(TestCase):

    def setUp(self):
        #self.vote_1 = Vote.objects.create(time=datetime.now(),title='vote 1')
        self.party_1 = Party.objects.create(name='party 1', number_of_seats=4)
        self.vote_1 = Vote.objects.create(title="vote 1", time=datetime.datetime.now())
        self.mks = []
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
        translation.activate(settings.LANGUAGE_CODE)
        visited_links = set()

        test_pages = [reverse('main'), reverse('vote-list'),
                      reverse('bill-list'), reverse('member-list'),
                      reverse('party-list')]
        for page in test_pages:

            links_to_visit = []
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)
            visited_links.add(page)
            for link in re.findall("href=\"(.*?)\"",res.content):
                self.failUnless(link, "There seems to be an empty link in %s (href='')" % page)
                if (link in visited_links) or (link.startswith("http")) or link.startswith("#"):
                    continue
                if link.startswith("./"):
                    link = link[2:]
                elif link.startswith("."):
                    link = link[1:]
                if not link.startswith("/"): # relative
                    link = "%s%s" % (page,link)
                links_to_visit.append(link)

            while links_to_visit:
                link = links_to_visit.pop()
                res0 = self.client.get(link)
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
