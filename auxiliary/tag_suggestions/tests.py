from django.test import TestCase
from auxiliary.models import TagSuggestion
from auxiliary.tag_suggestions import approve
from django.contrib.auth.models import User
from laws.models import Bill, Law
from tagging.models import Tag
from django.contrib.contenttypes.models import ContentType
from auxiliary.views import suggest_tag_post
from django.http.request import HttpRequest
from committees.models import CommitteeMeeting, Committee
from datetime import datetime

class TestApprove(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('user_1', 'user_1@example.com', '123456')
        law = Law.objects.create(title='law 1')
        self.bill = Bill.objects.create(stage='1', title='bill 1', law=law)

    def test_approve(self):
        tag_suggestion = TagSuggestion.objects.create(
            name='suggestion 1',
            suggested_by=self.user,
            object=self.bill
        )
        approve(None, None, [tag_suggestion])
        tag = Tag.objects.get(name=tag_suggestion.name)
        self.assertEqual(tag.name, tag_suggestion.name)
        tagged_item = tag.items.all()[0]
        self.assertEqual(tagged_item.object, self.bill)
        # after a successful approval the tag suggestion should be deleted
        self.assertEqual(0, TagSuggestion.objects.filter(name='suggestion 1').count())

    def test_approve_existing_tag(self):
        Tag.objects.create(name='suggestion 2')
        tag_suggestion = TagSuggestion.objects.create(
            name='suggestion 2',
            suggested_by=self.user,
            object=self.bill
        )
        approve(None, None, [tag_suggestion])

class TestForm(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('user_1', 'user_1@example.com', '123456')
        self.committee = Committee.objects.create(name='committee')
        self.committee_meeting = CommitteeMeeting.objects.create(committee=self.committee, date=datetime.now())
        self.committee_content_type = ContentType.objects.get_for_model(self.committee_meeting)

    def test_form(self):
        request = HttpRequest()
        request.POST = {
            'name': 'test form tag',
            'app_label': self.committee_content_type.app_label,
            'object_type': self.committee_content_type.model,
            'object_id': self.committee_meeting.id
        }
        request.method = 'POST'
        request.user = self.user
        suggest_tag_post(request)
        tag_suggestion = TagSuggestion.objects.get(name='test form tag')
        self.assertEqual(tag_suggestion.object, self.committee_meeting)
        self.assertEqual(tag_suggestion.suggested_by, self.user)
