import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from mks.models import Member, Party
from persons.models import GENDER_CHOICES
from committees.models import Committee

from . import consts
from .models import Suggestion


class SuggestionsTests(TestCase):

    MK_SITE = 'http://mk1.example.com'

    def setUp(self):
        self.member1 = Member.objects.create(name='mk_1')
        self.member2 = Member.objects.create(name='mk_2')
        self.regular_user = User.objects.create_user('reg_user')
        self.editor = User.objects.create_superuser(
            'admin', 'admin@example.com', 'passwd')
        self.party = Party.objects.create(name='party')
        self.committee = Committee.objects.create(name='comm')

    def test_set_suggestion(self):

        actions = [
            {
                'action': consts.SET,
                'subject': self.member1,
                'fields': {
                    'website': self.MK_SITE,
                    'gender': GENDER_CHOICES[0][0],
                    'current_party': self.party,
                }
            }
        ]
        suggestion = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=actions,
        )

        self.assertIsNone(self.member1.website)
        self.assertIsNone(self.member1.gender)
        self.assertIsNone(self.member1.current_party)
        suggestion.auto_apply(self.editor)

        mk = Member.objects.get(pk=self.member1.pk)
        self.assertEqual(mk.website, self.MK_SITE)
        self.assertEqual(mk.gender, GENDER_CHOICES[0][0])
        self.assertEqual(mk.current_party, self.party)

        suggestion = Suggestion.objects.get(pk=suggestion.pk)

        self.assertEqual(suggestion.resolved_status, consts.FIXED)
        self.assertEqual(suggestion.resolved_by, self.editor)
        self.assertIsNotNone(suggestion.resolved_at)

        # cleanup
        mk.website = None
        mk.gender = None
        mk.current_party = None
        mk.save()

        self.member1 = mk
        Suggestion.objects.all().delete()

    def test_m2m_add_remove_suggestion(self):
        # make sure we're starting clean
        self.assertEqual(self.committee.members.count(), 0)

        suggestion1 = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'subject': self.committee,
                    'action': consts.ADD,
                    'fields': {'members': self.member1}
                }
            ]
        )

        suggestion2 = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'subject': self.committee,
                    'action': consts.ADD,
                    'fields': {'members': self.member2}
                }
            ]
        )

        suggestion3 = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'subject': self.committee,
                    'action': consts.REMOVE,
                    'fields': {'members': self.member1}
                }
            ]
        )

        suggestion1.auto_apply(self.editor)
        self.assertItemsEqual(self.committee.members.all(), [self.member1])

        suggestion2.auto_apply(self.editor)
        self.assertItemsEqual(
            self.committee.members.all(), [self.member1, self.member2])

        suggestion3.auto_apply(self.editor)
        self.assertItemsEqual(self.committee.members.all(), [self.member2])

        # cleanup
        self.committee.members.clear()
        Suggestion.objects.all().delete()

    def test_create_and_m2m_suggestion(self):
        NAME = 'The cool MK'
        suggestion = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'action': consts.CREATE,
                    'fields': {
                        'name': NAME,
                        'current_party': self.party,
                    },
                    'subject': Member,
                },
                {
                    'action': consts.ADD,
                    'fields': {'committees': self.committee}
                },
            ]
        )

        m = suggestion.auto_apply(self.editor)

        self.assertEqual(m.name, NAME)
        self.assertEqual(m.current_party, self.party)
        self.assertItemsEqual(m.committees.all(), [self.committee])

        m.delete()
        Suggestion.objects.all().delete()

    def test_get_pending_suggestions(self):

        total = Suggestion.objects.get_pending_suggestions().count()
        self.assertEqual(total, 0)

        total_mk1 = Suggestion.objects.get_pending_suggestions_for(
            self.member1).count()
        self.assertEqual(total_mk1, 0)

        total_mk2 = Suggestion.objects.get_pending_suggestions_for(
            self.member2).count()
        self.assertEqual(total_mk2, 0)

        suggestion1 = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'action': consts.SET,
                    'fields': {'website': self.MK_SITE},
                    'subject': self.member1,
                },
            ]
        )

        suggestion2 = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'action': consts.SET,
                    'fields': {'website': self.MK_SITE},
                    'subject': self.member2,
                },
            ]
        )

        total = Suggestion.objects.get_pending_suggestions().count()
        self.assertEqual(total, 2)

        total_mk1 = Suggestion.objects.get_pending_suggestions_for(
            self.member1).count()
        self.assertEqual(total_mk1, 1)

        total_mk2 = Suggestion.objects.get_pending_suggestions_for(
            self.member2).count()
        self.assertEqual(total_mk2, 1)

        suggestion1.auto_apply(self.editor)

        total = Suggestion.objects.get_pending_suggestions().count()
        self.assertEqual(total, 1)

        total_mk1 = Suggestion.objects.get_pending_suggestions_for(
            self.member1).count()
        self.assertEqual(total_mk1, 0)

        suggestions_mks2 = Suggestion.objects.get_pending_suggestions_for(
            self.member2)
        total_mk2 = suggestions_mks2.count()
        self.assertEqual(total_mk2, 1)
        self.assertEqual(list(suggestions_mks2), [suggestion2])

        # cleanup
        Suggestion.objects.all().delete()

    def test_cant_auto_apply_freetext(self):
        suggestion = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            comment="A free text comment"
        )

        with self.assertRaises(ValueError):
            suggestion.auto_apply(self.editor)

        # cleanup
        Suggestion.objects.all().delete()

    def test_invalid_add_without_field(self):

        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[
                    {
                        'subject': self.committee,
                        'action': consts.ADD
                    }
                ],
            )

        # cleanup just to be on the safe side
        Suggestion.objects.all().delete()

    def test_free_text_without_content(self):
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user
            )

        # cleanup just to be on the safe side
        Suggestion.objects.all().delete()

    def test_invalid_action_fields_type(self):
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[
                    {
                        'subject': self.member1,
                        'action': consts.SET,
                        'fields': 'current_party',
                    }
                ]
            )

        # cleanup just to be on the safe side
        Suggestion.objects.all().delete()

    def test_invalid_action_without_valid_subject(self):
        # first test without subject
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[{'action': consts.SET}],
            )

        # Now test invalid subject (not a model instance)
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[{'action': consts.SET, 'subject': 'Moo'}],
            )

        # cleanup just to be on the safe side
        Suggestion.objects.all().delete()

    def test_invalid_action_withot_action(self):
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[{'subject': self.member1}],
            )

        # cleanup just to be on the safe side
        Suggestion.objects.all().delete()

    def test_invalid_fields(self):
        # invalid field name
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[
                    {
                        'subject': self.member1,
                        'action': consts.SET,
                        'fields': {'not_exists': 'bla bla'},
                    }
                ]
            )

        # test without model instance
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[
                    {
                        'subject': self.member1,
                        'action': consts.SET,
                        'fields': {'current_party': 'bla bla'},
                    }
                ]
            )

        # test with invalid model instance type
        with self.assertRaises(ValidationError):
            Suggestion.objects.create_suggestion(
                suggested_by=self.regular_user,
                actions=[
                    {
                        'subject': self.member1,
                        'action': consts.SET,
                        'fields': {'current_party': self.member2},
                    }
                ]
            )

    def test_pending_suggestions_count_view(self):
        c = Client()

        NAME = 'The chosen one'
        suggestion = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'action': consts.CREATE,
                    'fields': {
                        'name': NAME,
                        'current_party': self.party,
                    },
                    'subject': Member,
                },
            ]
        )

        response = c.get('/suggestions/pending_count/', {'for': 'mks.Member'})
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertEqual(data.items()[0][1], 1)

        m = suggestion.auto_apply(self.editor)

        response = c.get('/suggestions/pending_count/', {'for': 'mks.Member'})
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertFalse(data)

        m.delete()
        Suggestion.objects.all().delete()

    def test_can_auto_apply(self):

        NAME = 'The chosen one'

        suggestion = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            actions=[
                {
                    'action': consts.CREATE,
                    'fields': {
                        'name': NAME,
                        'current_party': self.party,
                    },
                    'subject': Member,
                },
            ]
        )

        self.assertTrue(suggestion.can_auto_apply)

        suggestion = Suggestion.objects.create_suggestion(
            suggested_by=self.regular_user,
            comment='Insert comment here'
        )

        self.assertFalse(suggestion.can_auto_apply)
