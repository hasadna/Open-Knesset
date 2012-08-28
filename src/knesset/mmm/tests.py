from django.test import TestCase
from knesset.settings import PROJECT_ROOT
from knesset.mks.models import Member
from knesset.committees.models import Committee
from knesset.mmm.models import Document, parse_json, text_lookup, verify
from datetime import datetime
import simplejson
import re

FP = open(PROJECT_ROOT + "/mmm/test_matches.json")
JSON = simplejson.load(FP)
OK_CANDIDATES = re.sub(r"\s+", r" " , " ".join(JSON[0]['candidates']))
OK_DATE = datetime.strptime(JSON[0]['date'], '%d/%m/%Y')

class MmmTest(TestCase):
    """ Testing mmm functions """

    def test_parse_json(self):
        """
        Tests data modification
        """

        j = parse_json(FP)


        self.assertEqual(OK_CANDIDATES, j[0]['candidates'])
        self.assertEqual(OK_DATE, j[0]['date'])

    def test_text_lookup(self):
        """
        Tests in text look up for mks and committees names
        """
        mk_name = u'\u05e8\u05d5\u05e0\u05d9\u05ea \u05ea\u05d9\u05e8\u05d5\u05e9'
        mks = Member.objects.create(name=mk_name)
        c = Committee.objects.create(name='c1')


        self.assertIn(mk_name, OK_CANDIDATES)

        mk = text_lookup(Member, OK_CANDIDATES)
        self.assertEqual(mks.id, mk[0])

        self.assertNotIn('c1', OK_CANDIDATES)

        committees = text_lookup(Committee, OK_CANDIDATES)
        self.assertEqual([], committees)

    def test_verify(self):
        """
        Tests verify method
        """
        o = JSON[0]
        mk_name = u'\u05e8\u05d5\u05e0\u05d9\u05ea \u05ea\u05d9\u05e8\u05d5\u05e9'
        mks = Member.objects.create(name=mk_name)
        mkses = [1]
        committees = []
        d1 = Document.objects.create(url=JSON[0]['url'], title=JSON[0]['title'],
                                     publication_date=OK_DATE, author_names=JSON[0]['author'])
        d1.req_mks.add(mks.id)

        self.assertEqual(o['url'], d1.url)
        self.assertEqual(o['title'], d1.title)
        self.assertEqual(OK_DATE, d1.publication_date)
        self.assertEqual(o['author'], d1.author_names)
        self.assertEqual(1, d1.req_mks.count())
        self.assertEqual(0, d1.req_committee.count())

        self.assertTrue(verify(o, [d1], mkses, committees))
