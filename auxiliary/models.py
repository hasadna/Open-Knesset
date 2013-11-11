from django.db import models
from django.utils.translation import ugettext_lazy as _
from tinymce import models as tinymce_models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from tagging.models import TaggedItem, Tag
from laws.models import Vote, Bill
from committees.models import CommitteeMeeting
from django.contrib.contenttypes import generic


ICON_CHOICES = (
    ('quote', _('Quote')),
    ('stat', _('Statistic')),
    ('hand', _('Hand')),
)


class TidbitManager(models.Manager):

    def get_query_set(self):
        return super(TidbitManager, self).get_query_set().filter(
            is_active=True).order_by('ordering')


class Tidbit(models.Model):
    """Entries for 'Did you know ?' section in the index page"""

    title = models.CharField(_('title'), max_length=40,
                             default=_('Did you know ?'))
    icon = models.CharField(_('Icon'), max_length=15, choices=ICON_CHOICES,
                            help_text=_('Image type if no image is uploaded'))
    content = tinymce_models.HTMLField(_('Content'))
    button_text = models.CharField(_('Button text'), max_length=100)
    button_link = models.CharField(_('Button link'), max_length=255)

    is_active = models.BooleanField(_('Active'), default=True)
    ordering = models.IntegerField(_('Ordering'), default=20, db_index=True)

    suggested_by = models.ForeignKey(User, verbose_name=_('Suggested by'),
                                     related_name='tidbits', blank=True,
                                     null=True)
    photo = models.ImageField(_('Photo'), upload_to='tidbits', max_length=200,
                              blank=True, null=True)

    objects = models.Manager()
    active = TidbitManager()

    class Meta:
        verbose_name = _('Tidbit')
        verbose_name_plural = _('Tidbits')

    def __unicode__(self):
        return u'{0.title} {0.content}'.format(self)


class Feedback(models.Model):
    "Stores generic feedback suggestions/problems"

    content = models.TextField(_('Content'))
    suggested_by = models.ForeignKey(User, verbose_name=_('Suggested by'),
                                     related_name='feedbacl', blank=True,
                                     null=True)
    ip_address = models.IPAddressField(_('IP Address'), blank=True, null=True)
    user_agent = models.TextField(_('user_agent'), blank=True, null=True)
    url = models.TextField(_('URL'))

    class Meta:
        verbose_name = _('Feedback message')
        verbose_name_plural = _('Feedback messages')

class TagSynonym(models.Model):
    tag = models.ForeignKey(Tag, related_name='synonym_proper_tag')
    synonym_tag = models.ForeignKey(Tag,related_name='synonym_synonym_tag',unique=True)

class TagSuggestion(models.Model):
    name = models.TextField(unique=True)
    suggested_by = models.ForeignKey(User, verbose_name=_('Suggested by'),
                                     related_name='tagsuggestion', blank=True,
                                     null=True)
    content_type = models.ForeignKey(ContentType)
    object_id    = models.PositiveIntegerField(db_index=True)
    object       = generic.GenericForeignKey('content_type', 'object_id')

def add_tags_to_related_objects(sender, instance, **kwargs):
    """
    When a tag is added to an object, we also tag other objects that are
    related.
    This currently only handles tagging of bills. When a bill is tagged it will
    tag related votes and related committee meetings.

    """
    obj = instance.object
    tag = instance.tag
    if type(obj) is Bill:
        # tag related votes
        vote_ctype = ContentType.objects.get_for_model(Vote)
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


post_save.connect(add_tags_to_related_objects, sender=TaggedItem)


def remove_tags_from_related_objects(sender, instance, **kwargs):
    obj = instance.object
    try:
        tag = instance.tag
    except Tag.DoesNotExist:  # the tag itself was deleted,
        return  # so we have nothing to do.
    if type(obj) is Bill:
        # untag related votes
        vote_ctype = ContentType.objects.get_for_model(Vote)
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


post_delete.connect(remove_tags_from_related_objects, sender=TaggedItem)
