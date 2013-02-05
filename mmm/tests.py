# -*- coding: utf-8 -*-
from datetime import datetime

from django.test import TestCase
from django.utils import simplejson
from knesset.settings import PROJECT_ROOT
from mks.models import Member
from committees.models import Committee
from mmm.models import Document, DocumentManager

MMM_FIXTURE = PROJECT_ROOT + "/testdata/mmm/test_mmm.json"

class MmmTest(TestCase):
    """ Testing mmm functions """

    def test_match(self):
        match =  {
            "entity_id": 10012,
            "docid": "m00079",
            "entity_name": "\u05de\u05d5\u05d2\u05e9 \u05d5\u05e2\u05d3\u05d4 \u05dc\u05d1\u05d7\u05d9\u05e0\u05ea \u05d1\u05e2\u05d9\u05d9\u05ea \u05d4\u05e2\u05d5\u05d1\u05d3\u05d9 \u05d4\u05d6\u05e8\u05d9 \u05d4 \u05d8\u05d1\u05ea \u05ea\u05e9\u05e1",
            "entity_type": "COMM",
            "url": "http://knesset.gov.il/mmm/data/pdf/m00079.pdf",
            "title": "\u05d4\u05e2\u05d5\u05d1\u05d3\u05d9\u05dd \u05d4\u05d6\u05e8\u05d9\u05dd \u05d1\u05e2\u05e0\u05e3 \u05d4\u05e1\u05d9\u05e2\u05d5\u05d3",
            "authors": [
              "\u05e0\u05d9\u05d1\u05d9 \u05e7\u05dc\u05d9\u05d9\u05df"
            ],
            "pub_date": "2000-01-01",
            "session_date": None,
            "heading": "\u05de\u05d5\u05d2\u05e9 \u05d5\u05e2\u05d3\u05d4 \u05dc\u05d1\u05d7\u05d9\u05e0\u05ea \u05d1\u05e2\u05d9\u05d9\u05ea \u05d4\u05e2\u05d5\u05d1\u05d3\u05d9 \u05d4\u05d6\u05e8\u05d9 \u05d4 \u05d8\u05d1\u05ea \u05ea\u05e9\u05e1"
          }


        match['date'] = datetime.strptime(match['pub_date'], '%Y-%m-%d').date()

        mmm_doc = Document.objects.create(
            url = match['url'],
            title = match['title'],
            publication_date = match['pub_date'],
            author_names = match['authors'],
        )


        m = Member.objects.create(name='name')
        m2 = Member.objects.create(name='name1')
        mks = [m.id, m2.id]
        committees = []
        mmm_doc.req_mks = mks

        self.assertEqual(set(mks), set(mmm_doc.req_mks.values_list('pk', flat=True)))
        doc = Document.objects.get(url=match['url'])

#        self.assertTrue(verify(match, i, mks, committees))
        m3 = Member.objects.create(name='name3')
        m4 = Member.objects.create(name='name4')
        mks2 = [m3.id, m4.id]
        self.assertNotEqual(mks2, list(doc.req_mks.values_list('pk', flat=True)))

    def test_import(self):
        try:
            Document.objects.all().delete()
        except:
            pass

        with open(MMM_FIXTURE) as f:
            j = simplejson.load(f)
            mks = set()
            comms = set()

            # collect mks/comm ids referenced in the fixture
            for match in j['objects']['matches']:
                if match['entity_type'] == "MK" and match['entity_id'] not in mks:
                    mks.add( match['entity_id'])

                if match['entity_type'] == "COMM" and match['entity_id'] not in comms:
                    comms.add( match['entity_id'])

        # create mks/comms with matching ids
        for id in mks:
            Member.objects.create(id=id,name="mk"+str(id))

        for id in comms:
            Committee.objects.create(id=id,name="mk"+str(id))

        # do the import
        Document.objects.from_json(j)

        # verify that all linked entities are referenced by the Document object
        for match in  j['objects']['matches']:
            doc = Document.objects.get(url=match['url'])
            self.assertEqual(doc.title,match['title'])

            if match['entity_type'] == "MK":
                self.assertTrue(match['entity_id'] in doc.req_mks.values_list('id', flat=True))
            elif match['entity_type'] == "COMM":
                self.assertTrue(match['entity_id'] in doc.req_committee.values_list('id', flat=True))

        # make sure the titles match
        for match in  j['objects']['documents']:
            doc = Document.objects.get(url=match['url'])
            self.assertEqual(doc.title,match['title']) # make sure it exists actually

        # checks schema version
        j['meta']['schema_version'][0] = 3
        try:
            Document.objects.from_json(j)
        except AssertionError:
            pass
        else:
            raise AssertionError("Didn't detect bad schema version")
