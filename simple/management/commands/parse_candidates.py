# -*- coding: utf-8 -*-
import urllib2
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from persons.models import Person, PersonAlias, Role

logger = logging.getLogger("open-knesset.parse_candidates")

class Parties(object):

    def __init__(self, url):
        self.url = url

    def import_party(self, name, link):
        print (u"loading {} candidates from {}".format(name, link))
        data = BeautifulSoup(urllib2.urlopen(link).read())
        # lose the leading ה from the party name
        party_name = name[1:] if name[0] == u'ה' else name
        ordinal = 1
        for i in data.find_all(attrs={"class": "candidate"}):
            person_name = i.string
            try:
                person = Person.objects.get(name=person_name)
            except Person.DoesNotExist:
                try:
                    person = PersonAlias.objects.get(name=person_name).person
                except PersonAlias.DoesNotExist:
                    person = Person.objects.create(name=person_name)


            role, created = Role.objects.get_or_create(start_date=datetime(2015, 1, 29),
                             org=u"הבחירות לכנסת ה-20",
                             person=person,
                             text=u"מקום {} ב{}".format(ordinal, party_name))
            if created:
                print (u"created a role for {}".format(person_name))
            ordinal += 1

    def parse(self):
        data = BeautifulSoup(urllib2.urlopen(self.url).read())
        for i in data.find_all(attrs={"class": "internallinkKnessetTitle"}):
            self.import_party(i.string,
                "http://bechirot.gov.il/election/Candidates/Pages/{}".format(i.a["href"]))

class Command(BaseCommand):
    """Parse Election candidates from their webpage http://bechirot.gov.il/election/Pages/CandidatesList.aspx"""

    args = ''
    help = 'Creates persons with appropiate roles from the official election page'
    base_url = "http://bechirot.gov.il/election/Candidates/Pages/default.aspx"

    def handle(self, *args, **options):

        logger.info("reading html from {}".format(self.base_url))
        parties = Parties(self.base_url)
        parties.parse()

