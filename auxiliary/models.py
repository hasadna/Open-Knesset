from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django.utils.translation import ugettext_lazy as _
from tagging.models import Tag
from tinymce import models as tinymce_models

from committees.models import CommitteeMeeting

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
    suggested_at = models.DateTimeField(verbose_name=_('Suggested at'),
                                        auto_now_add=True,
                                        blank=True,
                                        null=True)
    suggested_by = models.ForeignKey(User, verbose_name=_('Suggested by'),
                                     related_name='feedback', blank=True,
                                     null=True)
    ip_address = models.IPAddressField(_('IP Address'), blank=True, null=True)
    user_agent = models.TextField(_('user_agent'), blank=True, null=True)
    url = models.TextField(_('URL'))

    class Meta:
        verbose_name = _('Feedback message')
        verbose_name_plural = _('Feedback messages')


class TagSynonym(models.Model):
    tag = models.ForeignKey(Tag, related_name='synonym_proper_tag')
    synonym_tag = models.ForeignKey(Tag,
                                    related_name='synonym_synonym_tag',
                                    unique=True)


class TagSuggestion(models.Model):
    name = models.TextField(unique=True)
    suggested_by = models.ForeignKey(User, verbose_name=_('Suggested by'),
                                     related_name='tagsuggestion', blank=True,
                                     null=True)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    object = generic.GenericForeignKey('content_type', 'object_id')


class TagKeyphrase(models.Model):
    tag = models.ForeignKey('tagging.Tag')
    phrase = models.CharField(max_length=100, blank=False, null=False)

    def __unicode__(self):
        return u"%s - %s" % (self.tag, self.phrase)

# The following commented code is a part of an attempt to auto-tag
# that wasn't successful enough, mostly because a lot of interesting
# tags don't have enough training data.

# def create_tokens(list_of_strings):
#    tokens = defaultdict(lambda: 0)
#    for s in list_of_strings:
#        t = s.translate(trans_dict)
#        t = re.sub(' . ', ' ', t)  # remove single char 'words'
#        t = re.sub(' +', ' ', t)  # unify blocks of spaces
#        token_words = t.split(' ')
#        for i in range(len(token_words) - 1):
#            token = ' '.join(token_words[i:i + 2])  # token = a seq of 2 words
#            tokens[token] += 1
#    return tokens
#
#
# def tag_common_tokens(tag):
#    t = Vote.objects.filter(tagged_items__tag=tag).values_list('title', flat=True)
#    t = list(set(t))
#    l = len(t)
#    a = create_tokens(t)
#    for k, v in a.items():
#        if v < l / 6:
#            a.pop(k)
#    return a
#
#
# def create_tag_keyphrases(queryset, field_name):
#    skip_tokens = set()  # used to speed up create_tag_keyphrases
#    ct = ContentType.objects.get_for_model(queryset[:1][0])
#    for o in queryset:
#        t = o.__getattribute__(field_name).translate(trans_dict)
#        t = re.sub(' . ', ' ', t)  # remove single char 'words'
#        t = re.sub(' +', ' ', t)  # unify blocks of spaces
#        token_words = t.split(' ')
#        for i in range(len(token_words) - 1):
#            token = ' '.join(token_words[i:i + 2])  # a token is a seq of 2 words
#            if token in skip_tokens:  # we've already seen this is a bad token
#                continue
#            print token.encode('utf8')
#            filt = {"%s__contains" % field_name: token}
#            token_objs = queryset.filter(**filt)  # all other items that contain
#            token_objs_count = token_objs.count()
#            if token_objs_count < 8:  # this token is not common enough
#                print "token_objs_count %d | %s" % (token_objs_count, token.encode('utf8'))
#                skip_tokens.add(token)
#                continue
#            token_tags = TaggedItem.objects.filter(content_type=ct,
#                                                   object_id__in=token_objs)\
#                .distinct().values_list('tag', flat=True)
#            if len(token_tags) > 60:  # this token is too wide, give up
#                print "len token_tags %d | %s" % (len(token_tags), token.encode('utf8'))
#                skip_tokens.add(token)
#                continue
#            for tag in token_tags:  # check if tags are common
#                c = TaggedItem.objects.filter(content_type=ct,
#                                              object_id__in=token_objs,
#                                              tag=tag).count()
#                t = Tag.objects.get(pk=tag)
#                print t, float(c) / token_objs_count
#                if float(c) / token_objs_count > 0.75:
#                    print "\n***"
#                    print o, o
#                    print token.encode('utf8')
#                    print t, t in o.tags
#                    print token_objs
