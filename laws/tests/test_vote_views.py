# encoding: utf-8
#


import unittest
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.test import TestCase
from tagging.models import Tag, TaggedItem

from laws.models import Vote, Bill

just_id = lambda x: x.id
APP = 'laws'


class VoteViewsTest(TestCase):
    def setUp(self):
        super(VoteViewsTest, self).setUp()
        self.jacob = User.objects.create_user('jacob', 'jacob@example.com',
                                              'JKM')
        self.adrian = User.objects.create_user('adrian', 'adrian@example.com',
                                               'ADRIAN')
        g, created = Group.objects.get_or_create(name='Valid Email')
        self.jacob.groups.add(g)

        ct = ContentType.objects.get_for_model(Tag)
        p = Permission.objects.get(codename='add_tag', content_type=ct)
        self.adrian.user_permissions.add(p)

        self.vote_1 = Vote.objects.create(time=datetime(2001, 9, 11),
                                          title='vote 1')
        self.vote_2 = Vote.objects.create(time=datetime.now(),
                                          title='vote 2')
        self.bill_1 = Bill.objects.create(stage='1', title='Bill 1')
        self.bill_2 = Bill.objects.create(stage='1', title='Bill 2')
        self.tag_1 = Tag.objects.create(name='tag1')
        self.ti = TaggedItem._default_manager.create(tag=self.tag_1,
                                                     content_type=ContentType.objects.get_for_model(Vote),
                                                     object_id=self.vote_1.id)

    def teardown(self):
        super(VoteViewsTest, self).tearDown()

    def testVoteList(self):
        res = self.client.get(reverse('vote-list'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'laws/vote_list.html')
        object_list = res.context['object_list']
        self.assertEqual(map(just_id, object_list),
                         [self.vote_2.id, self.vote_1.id, ])

    def testVoteDetail(self):
        res = self.client.get(reverse('vote-detail',
                                      kwargs={'pk': self.vote_1.id}))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res,
                                'laws/vote_detail.html')
        self.assertEqual(res.context['vote'].id, self.vote_1.id)

    def test_attach_bill_as_pre(self):
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.post(reverse('vote-detail',
                                       kwargs={'pk': self.vote_1.id,}
                                       ),
                               {
                                   'user_input_type': 'add-bill',
                                   'vote_model': self.vote_1.id,
                                   'vote_type': 'pre vote',
                                   'bill_model': self.bill_1.id,
                               })
        self.assertEqual(res.status_code, 302)

        pre_votes = self.bill_1.pre_votes
        self.assertEqual(pre_votes.filter(id=self.vote_1.id).count(), 1)

        # cleanup
        self.bill_1.pre_votes.remove(self.vote_1)
        self.bill_1.update_stage()
        self.client.logout()

    def test_attach_bill_as_first(self):
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.post(reverse('vote-detail',
                                       kwargs={'pk': self.vote_1.id,}
                                       ),
                               {
                                   'user_input_type': 'add-bill',
                                   'vote_model': self.vote_1.id,
                                   'vote_type': 'first vote',
                                   'bill_model': self.bill_1.id,
                               })
        self.assertEqual(res.status_code, 302)

        # Reload the bill instance after stage updated
        self.bill_1 = Bill.objects.get(id=self.bill_1.id)

        self.assertEquals(self.bill_1.first_vote, self.vote_1)

        # cleanup
        self.bill_1.first_vote = None
        self.bill_1.update_stage()
        self.client.logout()

    def test_attach_bill_as_approval(self):
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.post(reverse('vote-detail',
                                       kwargs={'pk': self.vote_1.id,}
                                       ),
                               {
                                   'user_input_type': 'add-bill',
                                   'vote_model': self.vote_1.id,
                                   'vote_type': 'approve vote',
                                   'bill_model': self.bill_1.id,
                               })
        self.assertEqual(res.status_code, 302)

        # Reload the bill instance after stage updated
        self.bill_1 = Bill.objects.get(id=self.bill_1.id)

        self.assertEquals(self.bill_1.approval_vote, self.vote_1)

        # cleanup
        self.bill_1.approval_vote = None
        self.bill_1.update_stage()
        self.client.logout()

    def test_illegal_attach_bill_as_first(self):
        # Attach a vote to a bill as first vote
        self.bill_1.first_vote = self.vote_2
        self.bill_1.update_stage()

        # Try to attach another vote as first to same bill using form
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.post(reverse('vote-detail',
                                       kwargs={'pk': self.vote_1.id,}
                                       ),
                               {
                                   'user_input_type': 'add-bill',
                                   'vote_model': self.vote_1.id,
                                   'vote_type': 'first vote',
                                   'bill_model': self.bill_1.id,
                               })
        self.assertEqual(res.status_code, 200)

        # Verify that form is invalid
        form = res.context['bill_form']
        self.assertFalse(form.is_valid())

        # Reload the bill instance after stage updated
        self.bill_1 = Bill.objects.get(id=self.bill_1.id)

        # Verify bill's first vote has not been overwritten
        self.assertEqual(self.bill_1.first_vote, self.vote_2)

        # cleanup
        self.bill_1.first_vote = None
        self.bill_1.update_stage()
        self.client.logout()

    def test_illegal_attach_bill_as_approval(self):
        # Attach a vote to a bill as approval vote
        self.bill_1.approval_vote = self.vote_2
        self.bill_1.update_stage()

        # Try to attach another vote as approval to same bill using form
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.post(reverse('vote-detail',
                                       kwargs={'pk': self.vote_1.id,}
                                       ),
                               {
                                   'user_input_type': 'add-bill',
                                   'vote_model': self.vote_1.id,
                                   'vote_type': 'approve vote',
                                   'bill_model': self.bill_1.id,
                               })
        self.assertEqual(res.status_code, 200)

        # Verify that form is invalid
        form = res.context['bill_form']
        self.assertFalse(form.is_valid())

        # Reload the bill instance after stage updated
        self.bill_1 = Bill.objects.get(id=self.bill_1.id)

        # Verify bill's approval vote has not been overwritten
        self.assertEqual(self.bill_1.approval_vote, self.vote_2)

        # cleanup
        self.bill_1.approval_vote = None
        self.bill_1.update_stage()
        self.client.logout()

    def test_illegal_attach_same_vote_as_approval_twice(self):
        # Attach a vote to a bill as approval vote
        self.bill_1.approval_vote = self.vote_1
        self.bill_1.update_stage()

        # Try to attach the same vote as approval to another bill using form
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        res = self.client.post(reverse('vote-detail',
                                       kwargs={'pk': self.vote_1.id,}
                                       ),
                               {
                                   'user_input_type': 'add-bill',
                                   'vote_model': self.vote_1.id,
                                   'vote_type': 'approve vote',
                                   'bill_model': self.bill_2.id,
                               })
        self.assertEqual(res.status_code, 200)

        # Verify that form is invalid
        form = res.context['bill_form']
        self.assertFalse(form.is_valid())

        # Reload the bill instances after stage updates
        self.bill_1 = Bill.objects.get(id=self.bill_1.id)
        self.bill_2 = Bill.objects.get(id=self.bill_2.id)

        # Verify bill 2 approval vote has not been written
        self.assertNotEqual(self.bill_2.approval_vote, self.vote_1)

        # Verify bill 1 approval vote has not been deleted
        self.assertEqual(self.bill_1.approval_vote, self.vote_1)

        # cleanup
        self.bill_1.approval_vote = None
        self.bill_1.update_stage()
        self.bill_2.approval_vote = None
        self.bill_2.update_stage()
        self.client.logout()

    def test_vote_tag_cloud(self):
        res = self.client.get(reverse('vote-tags-cloud'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'laws/vote_tags_cloud.html')

    def test_add_tag_to_vote_login_required(self):
        url = reverse('add-tag-to-object',
                      kwargs={'app': APP, 'object_type': 'vote', 'object_id': self.vote_2.id})
        res = self.client.post(url, {'tag_id': self.tag_1})
        self.assertRedirects(res, "%s?next=%s" % (settings.LOGIN_URL, url), status_code=302)

    def test_add_tag_to_vote(self):
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        url = reverse('add-tag-to-object',
                      kwargs={'app': APP, 'object_type': 'vote', 'object_id': self.vote_2.id})
        res = self.client.post(url, {'tag_id': self.tag_1.id})
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.tag_1, self.vote_2.tags)

    @unittest.skip("creating tags currently disabled")
    def test_create_tag_permission_required(self):
        self.assertTrue(self.client.login(username='jacob', password='JKM'))
        url = reverse('create-tag',
                      kwargs={'app': APP, 'object_type': 'vote', 'object_id': self.vote_2.id})
        res = self.client.post(url, {'tag': 'new tag'})
        self.assertRedirects(res, "%s?next=%s" % (settings.LOGIN_URL, url), status_code=302)

    @unittest.skip("creating tags currently disabled")
    def test_create_tag(self):
        self.assertTrue(self.client.login(username='adrian', password='ADRIAN'))
        url = reverse('create-tag',
                      kwargs={'app': APP, 'object_type': 'vote', 'object_id': self.vote_2.id})
        res = self.client.post(url, {'tag': 'new tag'})
        self.assertEqual(res.status_code, 200)
        self.new_tag = Tag.objects.get(name='new tag')
        self.assertIn(self.new_tag, self.vote_2.tags)

    def tearDown(self):
        self.vote_1.delete()
        self.vote_2.delete()
        self.tag_1.delete()
        self.ti.delete()
