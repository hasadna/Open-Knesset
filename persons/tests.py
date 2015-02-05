from datetime import datetime, date

from django.test import TestCase
from unittest import skip

from .models import Person
from .admin import merge_persons
from mks.models import Member, Knesset


class PersonTests(TestCase):
    def setUp(self):
        self.knesset = Knesset.objects.create(
            number=1,
            start_date=date(2014,1,1))
        self.defaults = {
            'name': 'a name',
            'date_of_birth': date.today(),
            'family_status': 'XYZ',
            'place_of_residence': 'AAA',
            'phone': '000-1234',
            'gender': 'F',
        }

    def test_merge_persons(self):
        mk = Member.objects.create()
        mk_person = mk.person.all()[0]
        person = Person.objects.create(**self.defaults)
        person.roles.create(org="the org", text="title")

        merge_persons(None, None, Person.objects.filter(
            id__in=[person.id, mk_person.id]))
        with self.assertRaises(Person.DoesNotExist):
            Person.objects.get(id=person.id)

        for k,v in self.defaults.items():
            self.assertEqual(getattr(person, k), v)
        roles = mk_person.roles.all()
        self.assertEquals(roles.count(), 1)
        role = roles[0]
        self.assertEquals(role.org, "the org")

    def test_member_person_sync(self):
        """ Test member/person sync on member save() """
        mk = Member.objects.create(**self.defaults)

        self.assertGreater(mk.person.count(), 0)

        person = Person.objects.filter(mk=mk)[0]

        for field in self.defaults:
            self.assertEqual(getattr(mk, field), getattr(person, field))

        mk.delete()
