import re

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from tagging.models import TaggedItem, Tag

from auxiliary.models import TagKeyphrase
from committees.models import CommitteeMeeting
from knesset.utils import trans_clean


def add_tags_to_related_objects(sender, instance, **kwargs):
    """
    When a tag is added to an object, we also tag other objects that are
    related.
    This currently only handles tagging of bills. When a bill is tagged it will
    tag related votes and related committee meetings.

    """
    obj = instance.object
    tag = instance.tag
    bill_ctype = ContentType.objects.get(app_label='laws', model='bill')
    if type(obj) is bill_ctype.model_class():
        vote_ctype = ContentType.objects.get(app_label='laws', model='vote')
        # tag related votes
        for v in obj.pre_votes.all():
            (ti, created) = TaggedItem._default_manager.get_or_create(
                tag=tag,
                content_type=vote_ctype,
                object_id=v.id)
        v = obj.first_vote
        if v:
            (ti, created) = TaggedItem._default_manager.get_or_create(
                tag=tag,
                content_type=vote_ctype,
                object_id=v.id)
        v = obj.approval_vote
        if v:
            (ti, created) = TaggedItem._default_manager.get_or_create(
                tag=tag,
                content_type=vote_ctype,
                object_id=v.id)

        cm_ctype = ContentType.objects.get_for_model(CommitteeMeeting)
        for cm in obj.first_committee_meetings.all():
            (ti, created) = TaggedItem._default_manager.get_or_create(
                tag=tag,
                content_type=cm_ctype,
                object_id=cm.id)
        for cm in obj.second_committee_meetings.all():
            (ti, created) = TaggedItem._default_manager.get_or_create(
                tag=tag,
                content_type=cm_ctype,
                object_id=cm.id)


def remove_tags_from_related_objects(sender, instance, **kwargs):
    obj = instance.object
    try:
        tag = instance.tag
    except Tag.DoesNotExist:  # the tag itself was deleted,
        return  # so we have nothing to do.
    bill_ctype = ContentType.objects.get(app_label='laws', model='bill')
    if type(obj) is bill_ctype.model_class():
        vote_ctype = ContentType.objects.get(app_label='laws', model='vote')
        # untag related votes
        for v in obj.pre_votes.all():
            try:
                ti = TaggedItem._default_manager.get(
                    tag=tag,
                    content_type=vote_ctype,
                    object_id=v.id)
                ti.delete()
            except TaggedItem.DoesNotExist:
                pass
        v = obj.first_vote
        if v:
            try:
                ti = TaggedItem._default_manager.get(
                    tag=tag,
                    content_type=vote_ctype,
                    object_id=v.id)
                ti.delete()
            except TaggedItem.DoesNotExist:
                pass
        v = obj.approval_vote
        if v:
            try:
                ti = TaggedItem._default_manager.get(
                    tag=tag,
                    content_type=vote_ctype,
                    object_id=v.id)
                ti.delete()
            except TaggedItem.DoesNotExist:
                pass

        # untag related committee meetings
        cm_ctype = ContentType.objects.get_for_model(CommitteeMeeting)
        for cm in obj.first_committee_meetings.all():
            try:
                ti = TaggedItem._default_manager.get(
                    tag=tag,
                    content_type=cm_ctype,
                    object_id=cm.id)
                ti.delete()
            except TaggedItem.DoesNotExist:
                pass
        for cm in obj.second_committee_meetings.all():
            try:
                ti = TaggedItem._default_manager.get(
                    tag=tag,
                    content_type=cm_ctype,
                    object_id=cm.id)
                ti.delete()
            except TaggedItem.DoesNotExist:
                pass


def tag_vote(vote):
    vote_ctype = ContentType.objects.get(app_label='laws', model='vote')
    t = vote.title.translate(trans_clean)
    t = re.sub(' . ', ' ', t)
    t = re.sub(' +', ' ', t)
    for tag_phrase in TagKeyphrase.objects.select_related('tag').all():
        if tag_phrase.phrase in t:
            TaggedItem.objects.get_or_create(tag=tag_phrase.tag,
                                             content_type=vote_ctype,
                                             object_id=vote.id)


# def tagged_votes_titles(tags):
#     """returns a list representation of the titles (cleaned) of votes tagged
#        by the given tags. There are also lines for the tags themselves as
#        headers. Use the output to write to file"""
#     res = []
#     for tag in tags:
#         res.append("\n%s" % tag.name)
#         t = Vote.objects.filter(tagged_items__tag=tag).values_list('title', flat=True)
#         t = list(set(t))
#         for t0 in t:
#             t1 = t0.translate(trans_clean)
#             t1 = re.sub(' . ', ' ', t1)  # remove single char 'words'
#             t1 = re.sub(' +', ' ', t1)  # unify blocks of spaces
#             res.append(t1)
#     return res


post_save.connect(add_tags_to_related_objects, sender=TaggedItem)

post_delete.connect(remove_tags_from_related_objects, sender=TaggedItem)
