from datetime import datetime, date

from django.test import TestCase
from unittest import skip

from .models import Person
from mks.models import Member


class PersonTests(TestCase):
    def test_member_person_sync(self):
        """
        Test member/person sync on member save()
        """

        birth = date.today()

        defaults = {
            'name': 'The MK',
            'date_of_birth': birth,
            'family_status': 'XYZ',
            'place_of_residence': 'AAA',
            'phone': '000-1234',
            'fax': '999-8765',
            'gender': 'F',
        }
        mk = Member.objects.create(**defaults)

        self.assertGreater(mk.person.count(), 0)

        person = Person.objects.filter(mk=mk)[0]

        for field in defaults:
            self.assertEqual(getattr(mk, field), getattr(person, field))

        mk.delete()
