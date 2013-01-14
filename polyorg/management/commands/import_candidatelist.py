# encoding: utf-8
import logging, csv, itertools
from collections import namedtuple
from django.core.management.base import BaseCommand
from django.db import transaction
from polyorg.models import Candidate, CandidateList
#from mks.models import Member
from persons.models import Person
from links.models import Link, LinkType

logger = logging.getLogger("open-knesset.polyorg.import_candidatelist")

CandidateTuple = namedtuple('CandidateTuple', ['comments', 'candidate_wikipedia',
                   'party_youtube', 'mqg', 'party_facebook', 'party_manifest_url',
                   'party_website', 'party_image_url', 'mk_id', 'ordinal', 'name',
                   'ballot', 'list'])

class Command(BaseCommand):
    
    def _add_link_if_changed(self, cnd, record, link_arg, link_title, link_type, model_name):
        if getattr(cnd, link_arg):
            # Link exists in CSV
            # Check if such a link exists in DB
            links = Link.objects.filter(content_type__app_label='polyorg',
                                        content_type__model=model_name,
                                        object_pk=record.id)
            if links:
                # it does!
                link = links[0]
            else:
                # it doesn't - create it
                link = Link.objects.create(url=getattr(cnd, link_arg), title=link_title,
                                           content_object=record, link_type=link_type)
            if link.url <> getattr(cnd, link_arg):
                # Link URL different in CSV - update it!
                ##logger.info('Changing link %s for %s' % (link_title, (record.person.name if model_name=='candidate' else record.name)))
                link.url = getattr(cnd, link_arg)
                link.save()
    
    def _list_by_cnd(self, cnd):
        ls = CandidateList.objects.filter(name__exact = cnd.list)
        if ls:
            clist = ls[0]
        else:
            clist = CandidateList.objects.create(name = cnd.list, ballot = cnd.ballot)
        # update candidate fields, if changed, and add links
        if cnd.party_image_url:
            clist.img_url = cnd.party_image_url
            clist.save()
        youtube_type, _  = LinkType.objects.get_or_create(title='YouTube')
        facebook_type, _  = LinkType.objects.get_or_create(title='פייסבוק')
        default_type, _  = LinkType.objects.get_or_create(title='default')
        self._add_link_if_changed(cnd, clist, 'party_youtube', link_title='סרטון YouTube של הרשימה',
                                  link_type=youtube_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'party_facebook', link_title='דף פייסבוק של הרשימה',
                                  link_type=facebook_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'party_manifest_url', link_title='מצע הרשימה',
                                  link_type=default_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'party_website', link_title='אתר הרשימה',
                                  link_type=default_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'mqg', link_title='דף הרשימה באתר התנועה לאיכות השלטון',
                                  link_type=default_type, model_name='candidatelist')
        return clist

    def _person_by_cnd(self, cnd):
        persons = list(Person.objects.filter(name__exact = cnd.name))
        if cnd.mk_id:
            persons = list(Person.objects.filter(mk__id = cnd.mk_id)) + persons
        if persons:
            return persons[0]
        return Person.objects.create(name = cnd.name)

    @transaction.commit_on_success()
    def handle(self, *args, **options):
        # For each candidate:
        #    Build a Candidate object
        for csv_file in args:
            self.stdout.write('Import from %s\n' % (csv_file))
            for cnd in itertools.islice(map(CandidateTuple._make, csv.reader(open(csv_file, "rb"))), 1, None):
                clist = self._list_by_cnd(cnd)
                person = self._person_by_cnd(cnd)
                candidates = Candidate.objects.filter(person=person)
                if candidates:
                    candidate = candidates[0]
                else:
                    candidate = Candidate.objects.create(candidates_list = clist, person = person, ordinal = cnd.ordinal)
                # update candidate fields, if changed
                wiki_type, _  = LinkType.objects.get_or_create(title='ויקיפדיה')
                self._add_link_if_changed(cnd, candidate, 'candidate_wikipedia',
                                          link_title='ערך ויקיפדיה של המועמד',
                                          link_type=wiki_type, model_name='candidate')
