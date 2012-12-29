import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from actstream import action, follow, unfollow
from mks.models import Member
from laws.models import Bill
from committees.models import Committee
from agendas.models import Agenda

class TestProfile(TestCase):

    def setUp(self):
        self.jacob = User.objects.create_user('jacob', 'jacob@jacobian.org',
                                              'JKM')
        self.adrian = User.objects.create_user('adrian', 'adrian@example.com',
                                              'adrian')
        profile = self.adrian.get_profile()
        profile.public_profile = False
        profile.save()

    def testPublicProfile(self):
        res = self.client.get(reverse('public-profile',
                                 kwargs={'pk': self.jacob.id}))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res,
                                'user/public_profile.html')
        self.assertEqual(res.context['viewed_user'], self.jacob)
        res = self.client.get(reverse('public-profile',
                                 kwargs={'pk': self.adrian.id}))
        self.assertEqual(res.status_code, 200)
        self.assertFalse('"details"' in res.content) # seems like profile is
        # public, even though it should not be

    def testProfileList(self):
        res = self.client.get(reverse('profile-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res,'user/profile_list.html')
        self.assertEqual(len(res.context['object_list']), 1)

    def testSignup(self):
        res = self.client.post(reverse('register'), {'username': 'john',
                        'password1': '123', 'password2': '123',
                        'email': 'john@example.com', 'email_notification': 'D'},
                        follow = True)
        self.assertEqual(res.redirect_chain, [('http://testserver/users/edit-profile/', 302)])
        new = User.objects.get(username='john')
        new_profile = new.get_profile()
        self.assertEqual(new_profile.email_notification, 'D')

    def test_no_double_signup(self):
        "Don't allow new registration with an exiting email"

        res = self.client.post(
            reverse('register'), {
                'username': 'first_jack',
                'password1': '123', 'password2': '123',
                'email': 'double_jack@example.com',
                'email_notification': 'D'
            },
            follow=True)

        self.assertEqual(res.redirect_chain, [('http://testserver/users/edit-profile/', 302)])

        res = self.client.post(
            reverse('register'), {
                'username': 'double_jack',
                'password1': '123', 'password2': '123',
                'email': 'double_jack@example.com',
                'email_notification': 'D'
            },
            follow=True)
        # Now try to create another user with some email
        self.assertContains(res, 'errorlist')

    def tearDown(self):
        self.jacob.delete()
        self.adrian.delete()

class TestFollowing(TestCase):

    def setUp(self):
        self.jacob = User.objects.create_user('jacob', 'jacob@jacobian.org',
                                              'JKM')
        self.david = Member.objects.create(name='david', start_date=datetime.date(2010,1,1))

        self.yosef = Member.objects.create(name='yosef', start_date=datetime.date(2010,1,1))
        self.moshe = Member.objects.create(name='moshe', start_date=datetime.date(2010,1,1))
        self.agenda_1 = Agenda.objects.create(name='agenda_1')
        self.committee_1 = Committee.objects.create(name='c1')
        self.meeting_1 = self.committee_1.meetings.create(date=datetime.datetime.now(),
                                                         protocol_text='m1')
        self.meeting_1.create_protocol_parts()
        action.send(self.jacob, verb='farted', target=self.david)
        action.send(self.jacob, verb='hit', target=self.yosef)
        action.send(self.jacob, verb='hit', target=self.moshe)
        self.bill_1 = Bill.objects.create(stage='1', title='bill 1', popular_name="The Bill")

    def testUnfollowMeeting(self):
        follow(self.jacob, self.meeting_1)
        p = self.jacob.get_profile()
        self.assertEquals(len(p.meetings), 1)
        loggedin = self.client.login(username='jacob', password='JKM')
        self.assertTrue(loggedin)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'what': 'meeting',
                                     'id': self.meeting_1.id,
                                     'verb':'unfollow'})
        self.assertEquals(len(p.members), 0)

    def test_following_members(self):
        """Test the following and unfollowing members using the
           generic follow method.
        """
        p = self.jacob.get_profile()
        loggedin = self.client.login(username='jacob', password='JKM')
        self.assertTrue(loggedin)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'id': self.david.id,
                                     'what': 'member',
                                     'verb': 'follow'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(p.members[0], self.david)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'id': self.yosef.id,
                                     'what': 'member',
                                     'verb': 'follow'})
        self.assertEquals(len(p.members), 2)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'id': self.david.id,
                                     'what':'member',
                                     'verb':'unfollow'})
        self.assertEquals(len(p.members), 1)
        self.assertEquals(p.members[0], self.yosef)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'id': self.yosef.id,
                                     'what': 'member',
                                     'verb': 'unfollow'})
        self.assertEquals(len(p.members), 0)
        self.client.logout()

    def test_following_bills(self):
        """Test the following and unfollowing a bill using the
           generic follow method.
        """
        p = self.jacob.get_profile()
        loggedin = self.client.login(username='jacob', password='JKM')
        self.assertTrue(loggedin)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'id': self.bill_1.id,
                                     'what': 'bill',
                                     'verb': 'follow'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(p.bills[0], self.bill_1)
        response = self.client.post(reverse('user-follow-unfollow'),
                                    {'id': self.bill_1.id,
                                     'what': 'bill',
                                     'verb': 'unfollow'})
        self.assertEquals(len(p.bills), 0)
        self.client.logout()
        
    def test_is_following(self):
        """Test the is-following query"""
        
        p = self.jacob.get_profile()
        loggedin = self.client.login(username='jacob', password='JKM')
        self.assertTrue(loggedin)
        
        follow(self.jacob, self.bill_1)
        response = self.client.post(reverse('user-is-following'),
                                    {'id': self.bill_1.id,
                                     'what': 'bill'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, 'true')
        
        unfollow(self.jacob, self.bill_1)
        response = self.client.post(reverse('user-is-following'),
                                    {'id': self.bill_1.id,
                                     'what': 'bill'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, 'false')
        
        self.client.logout()
        

    def tearDown(self):
        self.jacob.delete()
        self.david.delete()
        self.yosef.delete()
        self.moshe.delete()
        self.bill_1.delete()
        self.agenda_1.delete()
        self.committee_1.delete()
        self.meeting_1.delete()

