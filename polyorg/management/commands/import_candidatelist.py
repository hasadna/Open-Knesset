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
                   'party_youtube', 'mqg', 'facebook', 'party_manifest_url', 'twitter',
                   'website', 'image_url', 'mk_id', 'ordinal', 'name',
                   'ballot', 'list'])

class Command(BaseCommand):
    
    def _add_link_if_changed(self, cnd, model, link_arg, link_title, link_type, model_name):
        if getattr(cnd, link_arg):
            # Link exists in CSV
            # Check if such a link exists in DB
            url = getattr(cnd, link_arg)
            try:
                Link.objects.get_or_create(url=url, defaults = {
                        'content_object': model,
                        'link_type': link_type,
                        'title': link_title })
            except Link.MultipleObjectsReturned:
                links = Link.objects.filter(url=url)
                for i in range(1,len(links)):
                    links[i].delete()

    def _list_by_cnd(self, cnd):
        ls = CandidateList.objects.filter(name__exact = cnd.list)
        if ls:
            clist = ls[0]
        else:
            clist = CandidateList.objects.create(name = cnd.list, ballot = cnd.ballot)
        youtube_type, _  = LinkType.objects.get_or_create(title='YouTube')
        default_type, _  = LinkType.objects.get_or_create(title='default')
        self._add_link_if_changed(cnd, clist, 'party_youtube', link_title='סרטון YouTube של הרשימה',
                                  link_type=youtube_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'party_manifest_url', link_title='מצע הרשימה',
                                  link_type=default_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'website', link_title='אתר הרשימה',
                                  link_type=default_type, model_name='candidatelist')
        self._add_link_if_changed(cnd, clist, 'mqg', link_title='דף הרשימה באתר התנועה לאיכות השלטון',
                                  link_type=default_type, model_name='candidatelist')
        return clist

    def _person_by_cnd(self, cnd):
        ''' use the mk_id (if there) or the name to return the person '''
        if cnd.mk_id:
            try:
                return Person.objects.get(mk_id = cnd.mk_id)
            except Person.DoesNotExist:
                pass
        try:
            return Person.objects.get_by_name(cnd.name)
        except Person.DoesNotExist:
            person =  Person(name = cnd.name)
            if cnd.mk_id: 
                person.mk_id = mk_id
            person.save()

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
                self._add_link_if_changed(cnd, person, 'candidate_wikipedia',
                                          link_title='ויקיפדיה',
                                          link_type=wiki_type, model_name='person')
                facebook_type, _  = LinkType.objects.get_or_create(title='פייסבוק')
                self._add_link_if_changed(cnd, person, 'facebook', link_title='פייסבוק',
                                          link_type=facebook_type, model_name='person')
                person.img_url = cnd.image_url
                person.save()
