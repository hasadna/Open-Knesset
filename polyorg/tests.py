"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from persons.models import Person
from models import Candidate, CandidateList


class CreationTest(TestCase):
    def setUp(self):
        self.persons = [
            Person.objects.create(name='Linus'),
            Person.objects.create(name='Guido'),
            Person.objects.create(name='Jacob'),
        ]

    def test_candidatelist(self):
        """
        Tests the creation of CandiateList and it's basic methods
        """
        cl1 = CandidateList.objects.create(name="Imagine", ballot="I")
        for p, i in zip(self.persons, range(1,len(self.persons)+1)):
            Candidate.objects.create(candidates_list=cl1, person=p, ordinal=i)
        cl1.save()
        self.assertFalse(cl1.member_ids)
        cl2 = CandidateList(name="Think", ballot="T", surplus_partner=cl1)
        cl2.save()
        self.assertEqual(cl1.surplus_partner, cl2)
        cl1.delete()
        cl2.delete()

    def teardown(self):
        for p in self.persons: p.delete()

