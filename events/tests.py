"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

import datetime
from datetime import timedelta

import vobject

from django.test import TestCase
from django.utils import translation
from django.utils import simplejson as json
from django.core.urlresolvers import reverse

from models import Event

now = datetime.datetime.now()

class SimpleTest(TestCase):
    def setUp(self):
        self.ev1 = Event.objects.create(when=now, what="ev1")
        self.ev2 = Event.objects.create(when=now + timedelta(days=1), when_over=now + timedelta(days=1,hours=2), when_over_guessed=False, what="future=%s" % ''.join(str(x % 10) for x in xrange(300)))
        self.ev3 = Event.objects.create(when=now + timedelta(days=1), what="ev3")

    def testFutureEvent(self):
        """
        Tests Event.is_future property.
        """
        tomorrow = now+datetime.timedelta(1)
        ev2 = Event.objects.create(when=tomorrow, what="ev2")
        self.assertTrue(ev2.is_future)
        ev2.delete()

    def testIcalenderSummaryLength(self):
        """
        Tests that the icalendar view uses summary_length
        correctly.
        """
        summary_length = 123
        res = self.client.get(reverse('event-icalendar', kwargs={'summary_length':summary_length}))
        self.assertEqual(res.status_code,200)
        vcal = vobject.base.readOne(res.content)
        for vevent in vcal.components():
            if vevent.name != 'VEVENT':
                continue
            if vevent.summary.value.startswith("future"):
                self.assertEqual(len(vevent.summary.value), summary_length)

    def testIcalenderGuessedEndWarning(self):
        """
        test the guessed end warning.
        """
        translation.activate('en')
        res = self.client.get(reverse('event-icalendar'))
        self.assertEqual(res.status_code,200)
        vcal = vobject.base.readOne(res.content)
        for vevent in vcal.components():
            if vevent.summary.value.startswith("future"):
                self.assertEqual(vevent.description.value, self.ev2.what)
            elif vevent.summary.value == "ev3":
                self.assertEqual(vevent.description.value,
                    'ev3\n\noknesset warnings:\nno end date data - guessed it to be 2 hours after start')
        translation.deactivate()

    def testAPIv2FutureEventsConsistency(self):
        """
        Test that APIv2 and APIv1 fetch the same future events.
        """
        res_v1 = self.client.get('/api/event/')
        self.assertEqual(res_v1.status_code, 200)
        res_v2 = self.client.get('/api/v2/event/', format = 'json')
        self.assertEqual(res_v2.status_code, 200)
        ids_v1 = set(x['what'] for x in json.loads(res_v1.content))
        ids_v2 = set(x['what'] for x in json.loads(res_v2.content))
        self.assertEqual(ids_v1, ids_v2)

    def testAPIv2Identity(self):
        """
        Test that APIv2 and APIv1 return the same data for each event.
        """
        for event_id in [self.ev1.id, self.ev2.id, self.ev3.id]:
            res_v1 = self.client.get('/api/event/%d/' % event_id)
            self.assertEqual(res_v1.status_code, 200)
            res_v2 = self.client.get('/api/v2/event/%d/' % event_id, format = 'json')
            self.assertEqual(res_v2.status_code, 200)
            event_v1 = json.loads(res_v1.content)
            event_v2 = json.loads(res_v2.content)
            self.assertEqual(event_v1['what'], event_v2['what'])
            # APIv2 return a more "accurate" result, so I need to trunk it
            self.assertEqual(event_v1['when'], event_v2['when'][:-3])
            self.assertEqual(event_v1['where'], event_v2['where'])

    def tearDown(self):
        self.ev1.delete()
        self.ev2.delete()
        self.ev3.delete()
