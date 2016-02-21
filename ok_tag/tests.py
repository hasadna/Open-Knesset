import datetime
import json

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core import cache
from django.core.urlresolvers import reverse
from django.test import TestCase
from tagging.models import Tag, TaggedItem

from committees.models import Committee, CommitteeMeeting
from laws.models import Vote, Bill, Law
from mks.models import Knesset, Member


class TagDetailViewTest(TestCase):
    def setUp(self):
        self.previous_knesset = Knesset.objects.create(number=1,
                                                       start_date=datetime.datetime.today() - datetime.timedelta(
                                                           days=3),
                                                       end_date=datetime.datetime.today() - datetime.timedelta(days=1))
        self.current_knesset = Knesset.objects.create(number=2,
                                                      start_date=datetime.datetime.today() - datetime.timedelta(days=1))
        self.committee_1 = Committee.objects.create(name='c1')
        self.committee_2 = Committee.objects.create(name='c2')
        self.meeting_1 = self._given_commitee_meeting(datetime.datetime.now(), "tm1", "tagged meeting")
        self.meeting_1.create_protocol_parts()
        self.meeting_3 = self._given_commitee_meeting(datetime.datetime.now(), 'untagged', "untagged2")
        self.meeting_3.create_protocol_parts()
        self.meeting_4 = self._given_commitee_meeting(datetime.datetime.now(), 'untagged', "tagged_as_2")
        self.meeting_4.create_protocol_parts()
        self.meeting_2 = self._given_commitee_meeting(datetime.datetime.now() - datetime.timedelta(days=2), 'm2',
                                                      "python")
        self.meeting_2.create_protocol_parts()

        self.jacob = self.given_user_exists('jacob@example.com', 'JKM', 'jacob')
        self.adrian = self.given_user_exists('adrian@example.com', 'ADRIAN', 'adrian')
        (self.group, created) = Group.objects.get_or_create(name='Valid Email')
        if created:
            self.group.save()
        self.group.permissions.add(Permission.objects.get(name='Can add annotation'))
        self.jacob.groups.add(self.group)

        ct = ContentType.objects.get_for_model(Tag)
        self.adrian.user_permissions.add(Permission.objects.get(codename='add_tag', content_type=ct))
        self.tag_1 = Tag.objects.create(name='tag1')
        self.tag_2 = Tag.objects.create(name='tag2')
        self.tag_3 = Tag.objects.create(name='tag3')

        self.vote_pre_time_1 = Vote.objects.create(title="vote pre time 1", time=datetime.datetime.now())
        self.vote_pre_time_2 = Vote.objects.create(title="vote pre time 2",
                                                   time=datetime.datetime.now() - datetime.timedelta(days=2))
        self.vote_pre_time_3 = Vote.objects.create(title="vote pre time 3", time=datetime.datetime.now())
        self.vote_pre_time_4 = Vote.objects.create(title="vote pre time 4", time=datetime.datetime.now())
        self.bill_pre_1 = Bill.objects.create(stage='1', title='bill pre 1')
        self.bill_pre_2 = Bill.objects.create(stage='1', title='bill pre 2')
        self.bill_pre_3 = Bill.objects.create(stage='1', title='bill pre 3')
        self.bill_pre_4 = Bill.objects.create(stage='1', title='bill pre 4')
        obj = self.bill_pre_1
        tag_name = 'tag1'
        self._given_object_is_tagged(obj, tag_name)
        self._given_object_is_tagged(self.bill_pre_2, 'tag1')
        self._given_object_is_tagged(self.bill_pre_4, 'tag2')
        self.bill_pre_1.pre_votes.add(self.vote_pre_time_1)
        self.bill_pre_2.pre_votes.add(self.vote_pre_time_2)
        self.bill_pre_3.pre_votes.add(self.vote_pre_time_3)
        self.bill_pre_4.pre_votes.add(self.vote_pre_time_4)

        self.vote_first_time_1 = Vote.objects.create(title="vote first time 1", time=datetime.datetime.now())
        self.vote_first_time_2 = Vote.objects.create(title="vote first time 2",
                                                     time=datetime.datetime.now() - datetime.timedelta(days=2))
        self.vote_first_time_3 = Vote.objects.create(title="vote first time 3", time=datetime.datetime.now())
        self.vote_first_time_4 = Vote.objects.create(title="vote first time 4", time=datetime.datetime.now())
        self.bill_first_1 = Bill.objects.create(stage='1', title='bill first 1')
        self.bill_first_2 = Bill.objects.create(stage='1', title='bill first 2')
        self.bill_first_3 = Bill.objects.create(stage='1', title='bill first 3')
        self.bill_first_4 = Bill.objects.create(stage='1', title='bill first 4')
        self._given_object_is_tagged(self.bill_first_1, 'tag1')
        self._given_object_is_tagged(self.bill_first_2, 'tag1')
        self._given_object_is_tagged(self.bill_first_4, 'tag2')
        self.bill_first_1.first_vote = self.vote_first_time_1
        self.bill_first_2.first_vote = self.vote_first_time_2
        self.bill_first_3.first_vote = self.vote_first_time_3
        self.bill_first_4.first_vote = self.vote_first_time_4
        self.bill_first_1.save()
        self.bill_first_2.save()
        self.bill_first_3.save()
        self.bill_first_4.save()

        self.vote_approval_time_1 = Vote.objects.create(title="vote approval time 1", time=datetime.datetime.now())
        self.vote_approval_time_2 = Vote.objects.create(title="vote approval time 2",
                                                        time=datetime.datetime.now() - datetime.timedelta(days=2))
        self.vote_approval_time_3 = Vote.objects.create(title="vote approval time 3", time=datetime.datetime.now())
        self.vote_approval_time_4 = Vote.objects.create(title="vote approval time 4", time=datetime.datetime.now())
        self.bill_approval_1 = Bill.objects.create(stage='1', title='bill approval 1')
        self.bill_approval_2 = Bill.objects.create(stage='1', title='bill approval 2')
        self.bill_approval_3 = Bill.objects.create(stage='1', title='bill approval 3')
        self.bill_approval_4 = Bill.objects.create(stage='1', title='bill approval 4')
        self._given_object_is_tagged(self.bill_approval_1, 'tag1')
        self._given_object_is_tagged(self.bill_approval_2, 'tag1')
        self._given_object_is_tagged(self.bill_approval_4, 'tag2')
        self.bill_approval_1.approval_vote = self.vote_approval_time_1
        self.bill_approval_2.approval_vote = self.vote_approval_time_2
        self.bill_approval_3.approval_vote = self.vote_approval_time_3
        self.bill_approval_4.approval_vote = self.vote_approval_time_4
        self.bill_approval_1.save()
        self.bill_approval_2.save()
        self.bill_approval_3.save()
        self.bill_approval_4.save()

        self.bill_first_meeting_1 = Bill.objects.create(stage='1', title='bill first meeting 1')
        self.bill_first_meeting_2 = Bill.objects.create(stage='1', title='bill first meeting 2')
        self.bill_first_meeting_3 = Bill.objects.create(stage='1', title='bill first meeting 3')
        self.bill_first_meeting_4 = Bill.objects.create(stage='1', title='bill first meeting 4')

        self.meeting_first_time_1 = self._given_commitee_meeting(datetime.datetime.now(), 'mf1', "meeting first 1")
        self.meeting_first_time_1.create_protocol_parts()
        self.meeting_first_time_2 = self._given_commitee_meeting(datetime.datetime.now() - datetime.timedelta(days=2),
                                                                 'mf2', "meeting first 2")
        self.meeting_first_time_2.create_protocol_parts()
        self.meeting_first_time_3 = self._given_commitee_meeting(datetime.datetime.now(), 'mf3', "meeting first 3")
        self.meeting_first_time_3.create_protocol_parts()
        self.meeting_first_time_4 = self._given_commitee_meeting(datetime.datetime.now(), 'mf4', "meeting first 4")
        self.meeting_first_time_4.create_protocol_parts()
        self._given_object_is_tagged(self.bill_first_meeting_1, 'tag1')
        self._given_object_is_tagged(self.bill_first_meeting_2, 'tag1')
        self._given_object_is_tagged(self.bill_first_meeting_4, 'tag2')
        self.bill_first_meeting_1.first_committee_meetings.add(self.meeting_first_time_1)
        self.bill_first_meeting_2.first_committee_meetings.add(self.meeting_first_time_2)
        self.bill_first_meeting_3.first_committee_meetings.add(self.meeting_first_time_3)
        self.bill_first_meeting_4.first_committee_meetings.add(self.meeting_first_time_4)
        self.bill_first_meeting_1.save()
        self.bill_first_meeting_2.save()
        self.bill_first_meeting_3.save()
        self.bill_first_meeting_4.save()

        self.bill_second_meeting_1 = Bill.objects.create(stage='1', title='bill second meeting 1')
        self.bill_second_meeting_2 = Bill.objects.create(stage='1', title='bill second meeting 2')
        self.bill_second_meeting_3 = Bill.objects.create(stage='1', title='bill second meeting 3')
        self.bill_second_meeting_4 = Bill.objects.create(stage='1', title='bill second meeting 4')
        self.meeting_second_time_1 = self._given_commitee_meeting(datetime.datetime.now(), 'ms1', "meeting second 1")
        self.meeting_second_time_1.create_protocol_parts()
        self.meeting_second_time_2 = self._given_commitee_meeting(datetime.datetime.now() - datetime.timedelta(days=2),
                                                                  'ms2', "meeting second 2")
        self.meeting_second_time_2.create_protocol_parts()
        self.meeting_second_time_3 = self._given_commitee_meeting(datetime.datetime.now(), 'ms3', "meeting second 3")
        self.meeting_second_time_3.create_protocol_parts()
        self.meeting_second_time_4 = self._given_commitee_meeting(datetime.datetime.now(), 'ms4', "meeting second 4")
        self.meeting_second_time_4.create_protocol_parts()
        self._given_object_is_tagged(self.bill_second_meeting_1, 'tag1')
        self._given_object_is_tagged(self.bill_second_meeting_2, 'tag1')
        self._given_object_is_tagged(self.bill_second_meeting_4, 'tag2')
        self.bill_second_meeting_1.first_committee_meetings.add(self.meeting_second_time_1)
        self.bill_second_meeting_2.first_committee_meetings.add(self.meeting_second_time_2)
        self.bill_second_meeting_3.first_committee_meetings.add(self.meeting_second_time_3)
        self.bill_second_meeting_4.first_committee_meetings.add(self.meeting_second_time_4)
        self.bill_second_meeting_1.save()
        self.bill_second_meeting_2.save()
        self.bill_second_meeting_3.save()
        self.bill_second_meeting_4.save()

        self.mk_1 = Member.objects.create(name='mk 1')
        self.topic = self.committee_1.topic_set.create(creator=self.jacob,
                                                       title="hello", description="hello world")

        cm_ct = ContentType.objects.get_for_model(CommitteeMeeting)

        self.meeting_1.mks_attended.add(self.mk_1)

        TaggedItem._default_manager.get_or_create(tag=self.tag_1, content_type=cm_ct, object_id=self.meeting_1.id)
        TaggedItem._default_manager.get_or_create(tag=self.tag_1, content_type=cm_ct, object_id=self.meeting_2.id)
        TaggedItem._default_manager.get_or_create(tag=self.tag_2, content_type=cm_ct, object_id=self.meeting_4.id)

        self.vote_time_1 = Vote.objects.create(title="vote time 1", time=datetime.datetime.now())
        self.vote_time_2 = Vote.objects.create(title="vote time 2",
                                               time=datetime.datetime.now() - datetime.timedelta(days=2))
        self.vote_time_3 = Vote.objects.create(title="vote time 3", time=datetime.datetime.now())
        self.vote_time_4 = Vote.objects.create(title="vote time 4", time=datetime.datetime.now())

        vote_ct = ContentType.objects.get_for_model(Vote)
        TaggedItem._default_manager.get_or_create(tag=self.tag_1, content_type=vote_ct, object_id=self.vote_time_1.id)
        TaggedItem._default_manager.get_or_create(tag=self.tag_1, content_type=vote_ct, object_id=self.vote_time_2.id)
        TaggedItem._default_manager.get_or_create(tag=self.tag_2, content_type=vote_ct, object_id=self.vote_time_4.id)

        self.bill_dup_second_meeting = Bill.objects.create(stage='1', title='bill dup second meeting')
        self.meeting_dup_second_time_1 = self._given_commitee_meeting(datetime.datetime.now(), 'ms1',
                                                                      "meeting second 1")
        self.meeting_dup_second_time_1.create_protocol_parts()
        self.meeting_dup_second_time_2 = self._given_commitee_meeting(datetime.datetime.now(), 'ms2',
                                                                      "meeting second 2")
        self.meeting_dup_second_time_2.create_protocol_parts()
        self._given_object_is_tagged(self.bill_dup_second_meeting, 'tag3')
        self.bill_dup_second_meeting.first_committee_meetings.add(self.meeting_dup_second_time_1)
        self.bill_dup_second_meeting.first_committee_meetings.add(self.meeting_dup_second_time_2)
        self.bill_dup_second_meeting.save()

    def _given_object_is_tagged(self, obj, tag_name):
        Tag.objects.add_tag(obj, tag_name)

    def _given_commitee_meeting(self, a_date, protocol_text, topics):
        return self.committee_1.meetings.create(date=a_date,
                                                topics=topics, protocol_text=protocol_text
                                                )

    def given_user_exists(self, email, password, username):
        return User.objects.create_user(username, email, password)

    def test_tag_detail_view_is_returned_for_valid_knesset_and_paginated_correctly(self):
        res = self.client.get(reverse('tag-detail', kwargs={'slug': 'tag1'}))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        knesset_id = res.context['knesset_id'].number
        self.assertEqual(knesset_id, 2)

    def test_invalid_knesset_id_returns_404(self):
        res = self.client.get(reverse('tag-detail', kwargs={'slug': 'tag1'}), {'knesset': 10})
        self.assertEqual(res.status_code, 404)

    def testCurrentSelectedKnessetId(self):
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 2)

        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        knesset_id = res.context['knesset_id'].number
        self.assertEqual(knesset_id, 2)

    def testPrevSelectedKnessetId(self):
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 1)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        knesset_id = res.context['knesset_id'].number
        self.assertEqual(knesset_id, 1)

    def _get_tag_detail_view_by_tag_and_knesset(self, tag, knesset_id):
        return self.client.get(reverse('tag-detail', kwargs={'slug': tag}), {'knesset': knesset_id})

    def _get_more_tagged_committees_by_tag_and_knesset(self, tag_id, knesset_id, page=1, initial=5):
        return self.client.get(reverse('tag-detail-more-committees', kwargs={'pk': tag_id}), {'knesset': knesset_id,
                                                                                              'page': page,
                                                                                              'initial': initial})

    def test_tagged_commitee_meetings_are_displayed_according_to_tag(self):
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 2)

        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        cms = res.context['cms']
        expected_cms = set([
            "meeting first 1",
            "meeting second 1",
            "tagged meeting",
        ])

        self.assertEqual(set([cm.topics for cm in cms]), expected_cms)
        more_committee_meetings = res.context['more_committee_meetings']

        self.assertFalse(more_committee_meetings)

    def test_tagged_committee_meetings_returns_more_option_if_more_then_10(self):
        meetings = CommitteeMeeting.objects.all()
        self.assertTrue(meetings.count() > 10)
        for meeting in meetings:
            self._given_object_is_tagged(meeting, 'tag1')
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 2)

        self.assertEqual(res.status_code, 200)

        more_committee_meetings = res.context['more_committee_meetings']

        self.assertTrue(more_committee_meetings)

    def test_more_tagged_meetings_returns_do_not_include_original_meetings(self):
        meetings = CommitteeMeeting.objects.all()
        self.assertTrue(meetings.count() > 10)
        meetings_count = meetings.count()
        for meeting in meetings:
            self._given_object_is_tagged(meeting, 'tag1')
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 2)

        self.assertEqual(res.status_code, 200)

        cms = res.context['cms']
        paginated_initial_return = 5
        self.assertEqual(len(cms), paginated_initial_return)
        tag = Tag.objects.get(name='tag1')
        more_response = self._get_more_tagged_committees_by_tag_and_knesset(tag.pk, knesset_id=2, page=1, initial=5)
        self.assertEqual(more_response.status_code, 200)
        more_data = json.loads(more_response.content)
        self.assertTrue(more_data['has_next'])
        self.assertEqual(more_data['current'], 1)
        self.assertEqual(more_data['total'], 3)

    def testVisibleBills(self):
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 2)

        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        bills = res.context['bills']
        expected_bills = set([
            "bill pre 1",
            "bill first 1",
            "bill approval 1",
            "bill first meeting 1",
            "bill second meeting 1",
        ])
        self.assertEqual(set([b.title for b in bills]), expected_bills)

    def testUniqueBills(self):
        res = self._get_tag_detail_view_by_tag_and_knesset('tag3', 2)

        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        bills = res.context['bills']
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0].title, "bill dup second meeting")

    def testVisibleVotes(self):
        res = self._get_tag_detail_view_by_tag_and_knesset('tag1', 2)

        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        votes = res.context['votes']
        expected_votes = set([
            "vote time 1",
            "vote approval time 1",
            "vote first time 1",
        ])
        self.assertEqual(set([v.title for v in votes]), expected_votes)

    def _tag_meeting(self, meeting, tag_name):
        pass


class TagVoteBillTagOrderTest(TestCase):
    def setUp(self):
        self.knesset1 = Knesset.objects.create(number=1,
                                               start_date=datetime.datetime.today() - datetime.timedelta(days=3),
                                               end_date=datetime.datetime.today() - datetime.timedelta(days=1))
        self.knesset2 = Knesset.objects.create(number=2,
                                               start_date=datetime.datetime.today() - datetime.timedelta(days=1))
        self.committee_1 = Committee.objects.create(name='c1')
        self.committee_2 = Committee.objects.create(name='c2')
        self.jacob = User.objects.create_user('jacob', 'jacob@example.com',
                                              'JKM')
        self.adrian = User.objects.create_user('adrian', 'adrian@example.com',
                                               'ADRIAN')
        (self.group, created) = Group.objects.get_or_create(name='Valid Email')
        if created:
            self.group.save()
        self.group.permissions.add(Permission.objects.get(name='Can add annotation'))
        self.jacob.groups.add(self.group)

        ct = ContentType.objects.get_for_model(Tag)
        self.adrian.user_permissions.add(Permission.objects.get(codename='add_tag', content_type=ct))
        self.tag_1 = Tag.objects.create(name='tag1')
        self.tag_2 = Tag.objects.create(name='tag2')

        self.vote_tag_before_vote = Vote.objects.create(title="vote tag before vote", time=datetime.datetime.now())
        self.bill_tag_before_vote = Bill.objects.create(stage='1', title='bill tag before vote')
        self.bill_tag_before_vote.save()
        Tag.objects.add_tag(self.bill_tag_before_vote, 'tag1')
        self.bill_tag_before_vote.approval_vote = self.vote_tag_before_vote
        self.bill_tag_before_vote.save()

        self.vote_tag_after_vote = Vote.objects.create(title="vote tag after vote", time=datetime.datetime.now())
        self.bill_tag_after_vote = Bill.objects.create(stage='1',
                                                       title='bill tag after vote')  # , approval_vote=self.vote_tag_after_vote)
        self.bill_tag_after_vote.approval_vote = self.vote_tag_after_vote
        self.bill_tag_after_vote.save()
        Tag.objects.add_tag(self.bill_tag_after_vote, 'tag1')

        self.vote_tag_after_vote_ctor = Vote.objects.create(title="vote tag after vote ctor",
                                                            time=datetime.datetime.now())
        self.bill_tag_after_vote_ctor = Bill.objects.create(stage='1', title='bill tag after vote ctor',
                                                            approval_vote=self.vote_tag_after_vote_ctor)
        self.vote_tag_after_vote_ctor.save()
        Tag.objects.add_tag(self.bill_tag_after_vote_ctor, 'tag1')

        self.vote_with_tag = Vote.objects.create(title="vote with tag", time=datetime.datetime.now())

        vote_ct = ContentType.objects.get_for_model(Vote)
        TaggedItem._default_manager.get_or_create(tag=self.tag_1, content_type=vote_ct, object_id=self.vote_with_tag.id)

    def testVisibleVotes(self):
        res = self.client.get(reverse('tag-detail', kwargs={'slug': 'tag1'}), {'page': 2})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'auxiliary/tag_detail.html')
        votes = res.context['votes']
        expected_votes = set([
            "vote with tag",
            "vote tag before vote",
            "vote tag after vote",
            "vote tag after vote ctor",
        ])
        self.assertEqual(set([v.title for v in votes]), expected_votes)


class TagResourceTest(TestCase):
    def setUp(self):
        cache.cache.clear()
        self.tags = []
        self.tags.append(Tag.objects.create(name='tag1'))
        self.tags.append(Tag.objects.create(name='tag2'))
        self.tags.append(Tag.objects.create(name='tag3'))

        self.vote = Vote.objects.create(title="vote 1", time=datetime.datetime.now())
        ctype = ContentType.objects.get_for_model(Vote)
        TaggedItem._default_manager.get_or_create(tag=self.tags[0], content_type=ctype, object_id=self.vote.id)
        TaggedItem._default_manager.get_or_create(tag=self.tags[1], content_type=ctype, object_id=self.vote.id)
        self.law = Law.objects.create(title='law 1')
        self.bill = Bill.objects.create(stage='1',
                                        stage_date=datetime.date.today(),
                                        title='bill 1',
                                        law=self.law)
        self.bill2 = Bill.objects.create(stage='2',
                                         stage_date=datetime.date.today(),
                                         title='bill 2',
                                         law=self.law)
        Tag.objects.add_tag(self.bill, 'tag1')
        Tag.objects.add_tag(self.bill2, 'tag3')

    def _reverse_api(self, name, **args):
        args.update(dict(api_name='v2', resource_name='tag'))
        return reverse(name, kwargs=args)

    def test_api_tag_list(self):
        res = self.client.get(self._reverse_api('api_dispatch_list'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)['objects']
        self.assertEqual(len(res_json), 3)
        self.assertEqual(set([x['name'] for x in res_json]), set(Tag.objects.values_list('name', flat=True)))

    def test_api_tag(self):
        res = self.client.get(self._reverse_api('api_dispatch_detail', pk=self.tags[0].id))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)
        self.assertEqual(res_json['name'], self.tags[0].name)

    def test_api_tag_not_found(self):
        res = self.client.get(self._reverse_api('api_dispatch_detail', pk=12345))
        self.assertEqual(res.status_code, 404)

    def test_api_tag_for_vote(self):
        res = self.client.get(self._reverse_api('tags-for-object', app_label='laws',
                                                object_type='vote', object_id=self.vote.id))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)['objects']
        self.assertEqual(len(res_json), 2)

    def test_api_related_tags(self):
        res = self.client.get(self._reverse_api('related-tags', app_label='laws',
                                                object_type='law', object_id=self.law.id, related_name='bills'))
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content)['objects']
        self.assertEqual(len(res_json), 2)
        received_tags = set(Tag.objects.get(pk=x) for x in (res_json[0]['id'], res_json[1]['id']))
        self.assertEqual(received_tags, set([self.tags[0], self.tags[2]]))
