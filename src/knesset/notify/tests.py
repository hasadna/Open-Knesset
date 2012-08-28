"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from datetime import datetime
from django.test import TestCase
from django.contrib.auth.models import User

from knesset.agendas.models import Agenda
from knesset.mks.models import Member
from knesset.laws.models import  Vote
from management.commands import notify
from actstream import follow, action


class SimpleTest(TestCase):
    def setUp(self):
        self.jacob = User.objects.create_user('jacob', 'jacob@example.com',
                                              'JKM')
        self.mk_1 = Member.objects.create(name='mk 1')
        self.agenda_1 = Agenda.objects.create(name='agenda 1')
        self.vote_1 = Vote.objects.create(time=datetime.now(),
                                          title='vote 1')

    def test_empty_email(self):
        cmd = notify.Command()
        email, email_html = cmd.get_email_for_user(self.jacob)
        self.assertEqual(email, [])
        follow (self.jacob, self.mk_1)
        action.send(self.mk_1, verb='farted on', target=self.agenda_1)
        email, email_html = cmd.get_email_for_user(self.jacob)
        text = "\n".join(email)
        self.assertIn(u'mk 1 farted on agenda 1', text) 
        follow (self.jacob, self.agenda_1)
        action.send(self.mk_1, verb='voted for', target=self.agenda_1)
        action.send(self.agenda_1, verb='supports', target=self.mk_1)
        email, email_html = cmd.get_email_for_user(self.jacob)
        text = "\n".join(email)
        self.assertIn(u'mk 1 voted for agenda 1', text) 
        self.assertIn(u'supports mk 1', text)
        email, email_html = cmd.get_email_for_user(self.jacob)
        self.assertEqual(email, [])
        


    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

