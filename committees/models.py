# encoding: utf-8
import re
import logging
from datetime import datetime, timedelta, date
from django.db import models
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.text import Truncator
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils.functional import cached_property
from django.conf import settings
from tagging.models import Tag, TaggedItem
from djangoratings.fields import RatingField

from committees.enums import CommitteeTypes
from events.models import Event
from links.models import Link
from mks.models import Knesset
from lobbyists.models import LobbyistCorporation
from itertools import groupby
from hebrew_numbers import gematria_to_int

from knesset_data_django.committees import members_extended

COMMITTEE_PROTOCOL_PAGINATE_BY = 120

logger = logging.getLogger("open-knesset.committees.models")


class Committee(models.Model):
    name = models.CharField(max_length=256)
    # comma separated list of names used as name aliases for harvesting
    aliases = models.TextField(null=True, blank=True)
    members = models.ManyToManyField('mks.Member', related_name='committees',
                                     blank=True)
    chairpersons = models.ManyToManyField('mks.Member',
                                          related_name='chaired_committees',
                                          blank=True)
    replacements = models.ManyToManyField('mks.Member',
                                          related_name='replacing_in_committees',
                                          blank=True)
    events = generic.GenericRelation(Event, content_type_field="which_type",
                                     object_id_field="which_pk")
    description = models.TextField(null=True, blank=True)
    portal_knesset_broadcasts_url = models.URLField(max_length=1000,
                                                    blank=True)
    type = models.CharField(max_length=10, default=CommitteeTypes.committee,
                            choices=CommitteeTypes.as_choices(),
                            db_index=True)
    hide = models.BooleanField(default=False)
    # Deprecated? In use? does not look in use
    protocol_not_published = models.BooleanField(default=False)
    knesset_id = models.IntegerField(null=True, blank=True)
    knesset_type_id = models.IntegerField(null=True, blank=True)
    knesset_parent_id = models.IntegerField(null=True, blank=True)
    # Deprecated? In use? does not look
    last_scrape_time = models.DateTimeField(null=True, blank=True)
    name_eng = models.CharField(max_length=256, null=True, blank=True)
    name_arb = models.CharField(max_length=256, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    knesset_description = models.TextField(null=True, blank=True)
    knesset_description_eng = models.TextField(null=True, blank=True)
    knesset_description_arb = models.TextField(null=True, blank=True)
    knesset_note = models.TextField(null=True, blank=True)
    knesset_note_eng = models.TextField(null=True, blank=True)
    knesset_portal_link = models.TextField(null=True, blank=True)

    @property
    def gender_presence(self):
        # returns a touple of (female_presence, male_presence
        r = {'F': 0, 'M': 0}
        for cm in self.meetings.all():
            try:
                results = groupby(cm.mks_attended.all(), lambda mk: mk.gender)
            except ValueError:
                continue
            for i in results:
                key, count = i[0], len(list(i[1]))
                r[key] += count
        return r['F'], r['M']

    def __unicode__(self):
        if self.type == 'plenum':
            return "%s" % ugettext('Plenum')
        else:
            return "%s" % self.name

    @models.permalink
    def get_absolute_url(self):
        if self.type == 'plenum':
            return 'plenum', []
        else:
            return 'committee-detail', [str(self.id)]

    @property
    def annotations(self):
        protocol_part_tn = ProtocolPart._meta.db_table
        meeting_tn = CommitteeMeeting._meta.db_table
        committee_tn = Committee._meta.db_table
        annotation_tn = Annotation._meta.db_table
        protocol_part_ct = ContentType.objects.get_for_model(ProtocolPart)
        ret = Annotation.objects.select_related().filter(
            content_type=protocol_part_ct)
        return ret.extra(tables=[protocol_part_tn,
                                 meeting_tn, committee_tn],
                         where=["%s.object_id=%s.id" % (
                             annotation_tn, protocol_part_tn),
                                "%s.meeting_id=%s.id" % (
                                    protocol_part_tn, meeting_tn),
                                "%s.committee_id=%%s" % meeting_tn],
                         params=[self.id]).distinct()

    def members_by_name(self, ids=None, current_only=False):
        """Return a queryset of all members, sorted by their name."""
        members = members_extended(self, current_only=current_only, ids=ids)
        return members.order_by('name')

    def recent_meetings(self, limit=10, do_limit=True):
        relevant_meetings = self.meetings.all().order_by('-date')
        if do_limit:
            more_available = relevant_meetings.count() > limit
            return relevant_meetings[:limit], more_available
        else:
            return relevant_meetings

    def future_meetings(self, limit=10, do_limit=True):
        current_date = datetime.now()
        relevant_events = self.events.filter(when__gt=current_date).order_by(
            'when')
        if do_limit:
            more_available = relevant_events.count() > limit
            return relevant_events[:limit], more_available
        else:
            return relevant_events

    def protocol_not_yet_published_meetings(self, end_date, limit=10,
                                            do_limit=True):
        start_date = self.meetings.all().order_by(
            '-date').first().date + timedelta(days=1) \
            if self.meetings.count() > 0 \
            else datetime.now()
        relevant_events = self.events.filter(when__gt=start_date,
                                             when__lte=end_date).order_by(
            '-when')

        if do_limit:
            more_available = relevant_events.count() > limit
            return relevant_events[:limit], more_available
        else:
            return relevant_events


not_header = re.compile(
    r'(^אני )|((אלה|אלו|יבוא|מאלה|ייאמר|אומר|אומרת|נאמר|כך|הבאים|הבאות):$)|(\(.\))|(\(\d+\))|(\d\.)'.decode(
        'utf8'))


def legitimate_header(line):
    """Returns true if 'line' looks like something should be a protocol part header"""
    if re.match(r'^\<.*\>\W*$', line):  # this is a <...> line.
        return True
    if not (line.strip().endswith(':')) or len(line) > 50 or not_header.search(
            line):
        return False
    return True


class CommitteeMeetingManager(models.Manager):
    def filter_and_order(self, *args, **kwargs):
        qs = self.all()
        # In dealing with 'tagged' we use an ugly workaround for the fact that generic relations
        # don't work as expected with annotations.
        # please read http://code.djangoproject.com/ticket/10461 before trying to change this code
        if kwargs.get('tagged'):
            if kwargs['tagged'] == ['false']:
                qs = qs.exclude(tagged_items__isnull=False)
            elif kwargs['tagged'] != ['all']:
                qs = qs.filter(tagged_items__tag__name__in=kwargs['tagged'])

        if kwargs.get('to_date'):
            qs = qs.filter(time__lte=kwargs['to_date'] + timedelta(days=1))

        if kwargs.get('from_date'):
            qs = qs.filter(time__gte=kwargs['from_date'])

        return qs.select_related('committee')


class CommitteesMeetingsOnlyManager(CommitteeMeetingManager):
    def get_queryset(self):
        return super(CommitteesMeetingsOnlyManager,
                     self).get_queryset().exclude(
            committee__type=CommitteeTypes.plenum)


class CommitteeMeeting(models.Model):
    committee = models.ForeignKey(Committee, related_name='meetings')
    date_string = models.CharField(max_length=256)
    date = models.DateField(db_index=True)
    mks_attended = models.ManyToManyField('mks.Member',
                                          related_name='committee_meetings')
    votes_mentioned = models.ManyToManyField('laws.Vote',
                                             related_name='committee_meetings',
                                             blank=True)
    protocol_text = models.TextField(null=True, blank=True)
    # the date the protocol text was last downloaded and saved
    protocol_text_update_date = models.DateField(blank=True, null=True)
    # the date the protocol parts were last parsed and saved
    protocol_parts_update_date = models.DateField(blank=True, null=True)
    topics = models.TextField(null=True, blank=True)
    src_url = models.URLField(max_length=1024, null=True, blank=True)
    tagged_items = generic.GenericRelation(TaggedItem,
                                           object_id_field="object_id",
                                           content_type_field="content_type")
    lobbyists_mentioned = models.ManyToManyField('lobbyists.Lobbyist',
                                                 related_name='committee_meetings',
                                                 blank=True)
    lobbyist_corporations_mentioned = models.ManyToManyField(
        'lobbyists.LobbyistCorporation',
        related_name='committee_meetings', blank=True)
    datetime = models.DateTimeField(db_index=True, null=True, blank=True)
    knesset_id = models.IntegerField(null=True, blank=True)

    objects = CommitteeMeetingManager()

    committees_only = CommitteesMeetingsOnlyManager()

    class Meta:
        ordering = ('-date',)
        verbose_name = _('Committee Meeting')
        verbose_name_plural = _('Committee Meetings')

    def title(self):
        truncator = Truncator(self.topics)
        return truncator.words(12)

    def __unicode__(self):
        cn = cache.get('committee_%d_name' % self.committee_id)
        if not cn:
            if self.committee.type == 'plenum':
                cn = 'Plenum'
            else:
                cn = unicode(self.committee)
            cache.set('committee_%d_name' % self.committee_id,
                      cn,
                      settings.LONG_CACHE_TIME)
        if cn == 'Plenum':
            return (u"%s" % (self.title())).replace("&nbsp;", u"\u00A0")
        else:
            return (u"%s - %s" % (cn,
                                  self.title())).replace("&nbsp;", u"\u00A0")

    @models.permalink
    def get_absolute_url(self):
        if self.committee.type == 'plenum':
            return 'plenum-meeting', [str(self.id)]
        else:
            return 'committee-meeting', [str(self.id)]

    def _get_tags(self):
        tags = Tag.objects.get_for_object(self)
        return tags

    def _set_tags(self, tag_list):
        Tag.objects.update_tags(self, tag_list)

    tags = property(_get_tags, _set_tags)

    def save(self, **kwargs):
        super(CommitteeMeeting, self).save(**kwargs)

    def create_protocol_parts(self, delete_existing=False, mks=None, mk_names=None):
        from knesset_data_django.committees.meetings import create_protocol_parts
        create_protocol_parts(self, delete_existing, mks, mk_names)

    def redownload_protocol(self):
        from knesset_data_django.committees.meetings import redownload_protocol
        redownload_protocol(self)

    def reparse_protocol(self, redownload=True, mks=None, mk_names=None):
        from knesset_data_django.committees.meetings import reparse_protocol
        reparse_protocol(self, redownload, mks, mk_names)

    def update_from_dataservice(self, dataservice_object=None):
        # TODO: obviousely broken, not sure what was here originaly and where it moved
        from committees.management.commands.scrape_committee_meetings import \
            Command as ScrapeCommitteeMeetingCommand
        from knesset_data.dataservice.committees import \
            CommitteeMeeting as DataserviceCommitteeMeeting
        if dataservice_object is None:
            ds_meetings = [
                ds_meeting for ds_meeting
                in DataserviceCommitteeMeeting.get(self.committee.knesset_id,
                                                   self.date - timedelta(
                                                       days=1),
                                                   self.date + timedelta(
                                                       days=1))
                if str(ds_meeting.id) == str(self.knesset_id)
                ]
            if len(ds_meetings) != 1:
                raise Exception(
                    'could not found corresponding dataservice meeting')
            dataservice_object = ds_meetings[0]
        meeting_transformed = ScrapeCommitteeMeetingCommand().get_committee_meeting_fields_from_dataservice(
            dataservice_object)
        [setattr(self, k, v) for k, v in meeting_transformed.iteritems()]
        self.save()

    @property
    def plenum_meeting_number(self):
        res = None
        parts = self.parts.filter(body__contains=u'ישיבה')
        if parts.count() > 0:
            r = re.search(u'ישיבה (.*)$', self.parts.filter(
                body__contains=u'ישיבה').first().body)
            if r:
                res = gematria_to_int(r.groups()[0])
        return res

    def plenum_link_votes(self):
        from laws.models import Vote
        if self.plenum_meeting_number:
            for vote in Vote.objects.filter(
                    meeting_number=self.plenum_meeting_number):
                for part in self.parts.filter(header__contains=u'הצבעה'):
                    r = re.search(r' (\d+)$', part.header)
                    if r and vote.vote_number == int(r.groups()[0]):
                        url = part.get_absolute_url()
                        Link.objects.get_or_create(
                            object_pk=vote.pk,
                            content_type=ContentType.objects.get_for_model(
                                Vote),
                            url=url,
                            defaults={
                                'title': u'לדיון בישיבת המליאה'
                            }
                        )

    def get_bg_material(self):
        """
            returns any background material for the committee meeting, or [] if none
        """
        import urllib2
        from BeautifulSoup import BeautifulSoup

        time = re.findall(r'(\d\d:\d\d)', self.date_string)[0]
        date = self.date.strftime('%d/%m/%Y')
        cid = self.committee.knesset_id
        if cid is None:  # missing this committee knesset id
            return []  # can't get bg material

        url = 'http://www.knesset.gov.il/agenda/heb/material.asp?c=%s&t=%s&d=%s' % (
            cid, time, date)
        data = urllib2.urlopen(url)
        bg_links = []
        if data.url == url:  # if no bg material exists we get redirected to a different page
            bgdata = BeautifulSoup(data.read()).findAll('a')

            for i in bgdata:
                bg_links.append(
                    {'url': 'http://www.knesset.gov.il' + i['href'],
                     'title': i.string})

        return bg_links

    @property
    def bg_material(self):
        return Link.objects.filter(object_pk=self.id,
                                   content_type=ContentType.objects.get_for_model(
                                       CommitteeMeeting).id)

    def find_attending_members(self, mks=None, mk_names=None):
        from knesset_data_django.committees.meetings import find_attending_members
        find_attending_members(self, mks, mk_names)

    @cached_property
    def main_lobbyist_corporations_mentioned(self):
        ret = []
        for corporation in self.lobbyist_corporations_mentioned.all():
            main_corporation = corporation.main_corporation
            if main_corporation not in ret:
                ret.append(main_corporation)
        for lobbyist in self.main_lobbyists_mentioned:
            latest_corporation = lobbyist.cached_data.get('latest_corporation')
            if latest_corporation:
                corporation = LobbyistCorporation.objects.get(
                    id=latest_corporation['id'])
                if corporation not in ret and corporation.main_corporation == corporation:
                    ret.append(corporation)
        return ret

    @cached_property
    def main_lobbyists_mentioned(self):
        return self.lobbyists_mentioned.all()


class ProtocolPartManager(models.Manager):
    def list(self):
        return self.order_by("order")


class ProtocolPart(models.Model):
    meeting = models.ForeignKey(CommitteeMeeting, related_name='parts')
    order = models.IntegerField()
    header = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    speaker = models.ForeignKey('persons.Person', blank=True, null=True,
                                related_name='protocol_parts')
    objects = ProtocolPartManager()
    type = models.TextField(blank=True, null=True, max_length=20)

    annotatable = True

    class Meta:
        ordering = ('order', 'id')

    def get_absolute_url(self):
        if self.order == 1:
            return self.meeting.get_absolute_url()
        else:
            page_num = 1 + (self.order - 1) / COMMITTEE_PROTOCOL_PAGINATE_BY
            if page_num == 1:  # this is on first page
                return "%s#speech-%d-%d" % (self.meeting.get_absolute_url(),
                                            self.meeting.id, self.order)
            else:
                return "%s?page=%d#speech-%d-%d" % (
                    self.meeting.get_absolute_url(),
                    page_num,
                    self.meeting.id, self.order)

    def __unicode__(self):
        return "%s %s: %s" % (self.meeting.committee.name, self.header,
                              self.body)


TOPIC_PUBLISHED, TOPIC_FLAGGED, TOPIC_REJECTED, \
TOPIC_ACCEPTED, TOPIC_APPEAL, TOPIC_DELETED = range(6)
PUBLIC_TOPIC_STATUS = (TOPIC_PUBLISHED, TOPIC_ACCEPTED)


class TopicManager(models.Manager):
    ''' '''
    get_public = lambda self: self.filter(status__in=PUBLIC_TOPIC_STATUS)

    by_rank = lambda self: self.extra(select={
        'rank': '((100/%s*rating_score/(1+rating_votes+%s))+100)/2' % (
            Topic.rating.range, Topic.rating.weight)
    }).order_by('-rank')

    def summary(self, order='-rank'):
        return self.filter(status__in=PUBLIC_TOPIC_STATUS).extra(select={
            'rank': '((100/%s*rating_score/(1+rating_votes+%s))+100)/2' % (
                Topic.rating.range, Topic.rating.weight)
        }).order_by(order)


class Topic(models.Model):
    '''
        Topic is used to hold the latest event about a topic and a committee

        Fields:
            title - the title
            description - its description
            created - the time a topic was first connected to a committee
            modified - last time the status or the message was updated
            editor - the user that entered the data
            status - the current status
            log - a text log that keeps text messages for status changes
            committees - defined using a many to many from `Committee`
    '''

    creator = models.ForeignKey(User)
    editors = models.ManyToManyField(User, related_name='editing_topics',
                                     null=True, blank=True)
    title = models.CharField(max_length=256,
                             verbose_name=_('Title'))
    description = models.TextField(blank=True,
                                   verbose_name=_('Description'))
    status = models.IntegerField(choices=(
        (TOPIC_PUBLISHED, _('published')),
        (TOPIC_FLAGGED, _('flagged')),
        (TOPIC_REJECTED, _('rejected')),
        (TOPIC_ACCEPTED, _('accepted')),
        (TOPIC_APPEAL, _('appeal')),
        (TOPIC_DELETED, _('deleted')),
    ), default=TOPIC_PUBLISHED)
    rating = RatingField(range=7, can_change_vote=True, allow_delete=True)
    links = generic.GenericRelation(Link, content_type_field="content_type",
                                    object_id_field="object_pk")
    events = generic.GenericRelation(Event, content_type_field="which_type",
                                     object_id_field="which_pk")
    # no related name as `topics` is already defined in CommitteeMeeting as text
    committees = models.ManyToManyField(Committee,
                                        verbose_name=_('Committees'))
    meetings = models.ManyToManyField(CommitteeMeeting, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    log = models.TextField(default="", blank=True)

    class Meta:
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')

    @models.permalink
    def get_absolute_url(self):
        return 'topic-detail', [str(self.id)]

    def __unicode__(self):
        return "%s" % self.title

    objects = TopicManager()

    def set_status(self, status, message=''):
        self.status = status
        self.log = '\n'.join(
            (u'%s: %s' % (self.get_status_display(), datetime.now()),
             u'\t%s' % message,
             self.log,)
        )
        self.save()

    def can_edit(self, user):
        return user.is_superuser or user == self.creator or \
               user in self.editors.all()


from listeners import *
