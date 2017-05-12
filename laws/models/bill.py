# encoding: utf-8
import logging
import random
from datetime import date

import voting
import waffle
from actstream import Follow, Action, action
from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import models
from django.db.utils import IntegrityError
from django.utils.translation import ugettext_lazy as _
from tagging.models import TaggedItem, Tag
from tagging.utils import get_tag

from knesset.utils import slugify_name
from laws.constants import FIRST_KNESSET_START, CONVERT_TO_DISCUSSION_HEADERS
from laws.enums import BillStages
from laws.models.proposal import PrivateProposal, KnessetProposal, GovProposal
from laws.vote_choices import BILL_AGRR_STAGES, BILL_STAGE_CHOICES, BILL_STAGES
from mks.models import Knesset

logger = logging.getLogger("open-knesset.laws.models")


class BillManager(models.Manager):
    use_for_related_fields = True

    def get_bills_by_private_proposal_date_for_member(self, date_range, member):
        proposals = self._get_private_proposals_for_member_for_date_range(member, date_range)

        return self.get_queryset().filter(proposals__in=proposals)

    def filter_and_order(self, *args, **kwargs):
        stage = kwargs.get('stage', None)
        member = kwargs.get('member', None)
        pp_id = kwargs.get('pp_id', None)
        knesset_booklet = kwargs.get('knesset_booklet', None)
        gov_booklet = kwargs.get('gov_booklet', None)
        changed_after = kwargs.get('changed_after', None)
        changed_before = kwargs.get('changed_before', None)
        bill_type = kwargs.get('bill_type', 'all')
        knesset_id = kwargs.get('knesset_id', 'all')

        filter_kwargs = {}

        if stage and stage != 'all':
            if stage in BILL_AGRR_STAGES:
                qs = self.filter(BILL_AGRR_STAGES[stage])
            else:
                filter_kwargs['stage__startswith'] = stage
                qs = self.filter(**filter_kwargs)
        else:
            qs = self.all()

        if knesset_id and knesset_id != 'all':
            knesset = Knesset.objects.get(number=int(knesset_id))
            period_start = knesset.start_date
            period_end = knesset.end_date or date.today()
            if waffle.switch_is_active('use_old_statistics'):
                qs = qs.filter(stage_date__range=(period_start, period_end))

            else:
                qs = self._filter_bills_by_proposal_date(member, period_end, period_start, qs)

        if kwargs.get('tagged', None):
            if kwargs['tagged'] == 'false':
                ct = ContentType.objects.get_for_model(Bill)
                filter_tagged = TaggedItem.objects.filter(content_type=ct).distinct().values_list('object_id',
                                                                                                  flat=True)
                qs = qs.exclude(id__in=filter_tagged)
            elif kwargs['tagged'] != 'all':
                qs = TaggedItem.objects.get_by_model(qs, get_tag(kwargs['tagged']))

        if bill_type == 'government':
            qs = qs.exclude(gov_proposal=None)
        elif bill_type == 'knesset':
            qs = qs.exclude(knesset_proposal=None)

        elif bill_type == 'private':
            qs = qs.exclude(proposals=None)

        if pp_id:
            private_proposals = PrivateProposal.objects.filter(
                proposal_id=pp_id).values_list(
                'id', flat=True)
            if private_proposals:
                qs = qs.filter(proposals__in=private_proposals)
            else:
                qs = qs.none()

        if knesset_booklet:
            knesset_proposals = KnessetProposal.objects.filter(
                booklet_number=knesset_booklet).values_list(
                'id', flat=True)
            if knesset_proposals:
                qs = qs.filter(knesset_proposal__in=knesset_proposals)
            else:
                qs = qs.none()
        if gov_booklet:
            government_proposals = GovProposal.objects.filter(
                booklet_number=gov_booklet).values_list('id', flat=True)
            if government_proposals:
                qs = qs.filter(gov_proposal__in=government_proposals)
            else:
                qs = qs.none()

        if changed_after:
            qs = qs.filter(stage_date__gte=changed_after)

        if changed_before:
            qs = qs.filter(stage_date__lte=changed_before)

        return qs

    def _filter_bills_by_proposal_date(self, member, period_end, period_start, qs):
        if not member:

            qs = qs.filter(stage_date__range=(period_start, period_end))
        else:
            proposals = self._get_private_proposals_for_member_for_date_range(member, (period_start, period_end))
            qs = qs.filter(proposals__in=proposals)
        return qs

    def _get_private_proposals_for_member_for_date_range(self, member, date_range):
        return PrivateProposal.objects.filter(date__range=date_range, proposers=member)


class Bill(models.Model):
    title = models.CharField(max_length=1000)
    full_title = models.CharField(max_length=2000, blank=True)
    slug = models.SlugField(max_length=1000)
    popular_name = models.CharField(max_length=1000, blank=True)
    popular_name_slug = models.CharField(max_length=1000, blank=True)
    law = models.ForeignKey('laws.Law', related_name="bills", blank=True, null=True)
    stage = models.CharField(max_length=10, choices=BILL_STAGE_CHOICES)
    #: date of entry to current stage
    stage_date = models.DateField(blank=True, null=True, db_index=True)
    pre_votes = models.ManyToManyField('laws.Vote', related_name='bills_pre_votes', blank=True,
                                       null=True)  # link to pre-votes related to this bill
    first_committee_meetings = models.ManyToManyField('committees.CommitteeMeeting', related_name='bills_first',
                                                      blank=True,
                                                      null=True)  # CM related to this bill, *before* first vote
    first_vote = models.ForeignKey('laws.Vote', related_name='bills_first', blank=True,
                                   null=True)  # first vote of this bill
    second_committee_meetings = models.ManyToManyField('committees.CommitteeMeeting', related_name='bills_second',
                                                       blank=True,
                                                       null=True)  # CM related to this bill, *after* first vote
    approval_vote = models.OneToOneField('laws.Vote', related_name='bill_approved', blank=True,
                                         null=True)  # approval vote of this bill
    proposers = models.ManyToManyField('mks.Member', related_name='bills', blank=True,
                                       null=True)  # superset of all proposers of all private proposals related to this bill
    joiners = models.ManyToManyField('mks.Member', related_name='bills_joined', blank=True,
                                     null=True)  # superset of all joiners

    objects = BillManager()

    class Meta:
        app_label = 'laws'
        ordering = ('-stage_date', '-id')
        verbose_name = _('Bill')
        verbose_name_plural = _('Bills')

    def __unicode__(self):
        return u"%s %s (%s)" % (self.law, self.title, self.get_stage_display())

    @models.permalink
    def get_absolute_url(self):
        return ('bill-detail', [str(self.id)])

    def save(self, **kwargs):
        self.slug = slugify_name(self.title)
        self.popular_name_slug = slugify_name(self.popular_name)
        if self.law:
            self.full_title = "%s %s" % (self.law.title, self.title)
        else:
            self.full_title = self.title
        super(Bill, self).save(**kwargs)
        for mk in self.proposers.all():
            mk.recalc_bill_statistics()

    def _get_tags(self):
        tags = Tag.objects.get_for_object(self)
        return tags

    def _set_tags(self, tag_list):
        Tag.objects.update_tags(self, tag_list)

    tags = property(_get_tags, _set_tags)

    def merge(self, another_bill):
        """Merges another_bill into self, and delete another_bill"""
        if not self.id:
            logger.debug('trying to merge into a bill with id=None, title=%s',
                         self.title)
            self.save()
        if not another_bill.id:
            logger.debug('trying to merge a bill with id=None, title=%s',
                         another_bill.title)
            another_bill.save()

        if self is another_bill:
            logger.debug('abort merging bill %d into itself' % self.id)
            return
        logger.debug('merging bill %d into bill %d' % (another_bill.id,
                                                       self.id))

        other_kp = KnessetProposal.objects.filter(bill=another_bill)
        my_kp = KnessetProposal.objects.filter(bill=self)
        if my_kp and other_kp:
            logger.debug('abort merging bill %d into bill %d, because both '
                         'have KPs' % (another_bill.id, self.id))
            return

        for pv in another_bill.pre_votes.all():
            self.pre_votes.add(pv)
        for cm in another_bill.first_committee_meetings.all():
            self.first_committee_meetings.add(cm)
        if not self.first_vote and another_bill.first_vote:
            self.first_vote = another_bill.first_vote
        for cm in another_bill.second_committee_meetings.all():
            self.second_committee_meetings.add(cm)
        if not self.approval_vote and another_bill.approval_vote:
            self.approval_vote = another_bill.approval_vote
        for m in another_bill.proposers.all():
            self.proposers.add(m)
        for pp in another_bill.proposals.all():
            pp.bill = self
            pp.save()
        if other_kp:
            other_kp[0].bill = self
            other_kp[0].save()

        bill_ct = ContentType.objects.get_for_model(self)
        Comment.objects.filter(content_type=bill_ct,
                               object_pk=another_bill.id).update(
            object_pk=self.id)
        for v in voting.models.Vote.objects.filter(content_type=bill_ct,
                                                   object_id=another_bill.id):
            if voting.models.Vote.objects.filter(content_type=bill_ct,
                                                 object_id=self.id,
                                                 user=v.user).count() == 0:
                # only if this user did not vote on self, copy the vote from
                # another_bill
                v.object_id = self.id
                v.save()
        for f in Follow.objects.filter(content_type=bill_ct,
                                       object_id=another_bill.id):
            try:
                f.object_id = self.id
                f.save()
            except IntegrityError:  # self was already being followed by the
                # same user
                pass
        for ti in TaggedItem.objects.filter(content_type=bill_ct,
                                            object_id=another_bill.id):
            if ti.tag not in self.tags:
                ti.object_id = self.id
                ti.save()
        for ab in another_bill.agendabills.all():
            try:
                ab.bill = self
                ab.save()
            except IntegrityError:  # self was already in this agenda
                pass
        for be in another_bill.budget_ests.all():
            try:
                be.bill = self
                be.save()
            except IntegrityError:  # same user already estimated self
                pass
        another_bill.delete()
        self.update_stage()

    def update_votes(self):
        used_votes = []  # ids of votes already assigned 'roles', so we won't match a vote in 2 places
        gp = GovProposal.objects.filter(bill=self)
        if gp:
            gp = gp[0]
            for this_v in gp.votes.all():
                if this_v.title.find('אישור'.decode('utf8')) == 0:
                    self.approval_vote = this_v
                    used_votes.append(this_v.id)
                if this_v.title.find('להעביר את'.decode('utf8')) == 0 and this_v.id not in used_votes:
                    self.first_vote = this_v
                    used_votes.append(this_v.id)

        kp = KnessetProposal.objects.filter(bill=self)
        if kp:
            for this_v in kp[0].votes.all():
                if this_v.title.find('אישור'.decode('utf8')) == 0 and this_v.id not in used_votes:
                    self.approval_vote = this_v
                    used_votes.append(this_v.id)
                if this_v.title.find('להעביר את'.decode('utf8')) == 0 and this_v.id not in used_votes:
                    if this_v.time.date() > kp[0].date:
                        self.first_vote = this_v
                    else:
                        self.pre_votes.add(this_v)
                    used_votes.append(this_v.id)
        pps = PrivateProposal.objects.filter(bill=self)
        if pps:
            for pp in pps:
                for this_v in pp.votes.all():
                    if this_v.title.find('אישור'.decode('utf8')) == 0 and this_v.id not in used_votes:
                        self.approval_vote = this_v
                        used_votes.append(this_v.id)
                    if this_v.title.find('להעביר את'.decode('utf8')) == 0 and this_v.id not in used_votes:
                        if self.stage == BillStages.PROPOSED:
                            self.pre_votes.add(this_v)
                        elif self.stage == BillStages.PRE_APPROVED:
                            self.first_vote = this_v

                        used_votes.append(this_v.id)
        self.update_stage()

    def update_stage(self, force_update=False):
        """
        Updates the stage for this bill according to all current data
        force_update - assume current stage is wrong, and force
        recalculation. default is False, so we assume current status is OK,
        and only look for updates.
        """
        if not self.stage_date or force_update:  # might be empty if bill is new
            self.stage_date = FIRST_KNESSET_START
        if self.approval_vote:
            if self.approval_vote.for_votes_count > self.approval_vote.against_votes_count:
                self.stage = BillStages.APPROVED
            else:
                self.stage = BillStages.FAILED_APPROVAL
            self.stage_date = self.approval_vote.time.date()
            self.save()
            return
        for cm in self.second_committee_meetings.all():
            if not self.stage_date or self.stage_date < cm.date:
                self.stage = BillStages.COMMITTEE_CORRECTIONS
                self.stage_date = cm.date
        if self.stage == BillStages.COMMITTEE_CORRECTIONS:
            self.save()
            return
        if self.first_vote:
            if self.first_vote.for_votes_count > self.first_vote.against_votes_count:
                self.stage = BillStages.FIRST_VOTE
            else:
                self.stage = BillStages.FAILED_FIRST_VOTE
            self.stage_date = self.first_vote.time.date()
            self.save()
            return
        try:
            kp = self.knesset_proposal
            if not (self.stage_date) or self.stage_date < kp.date:
                self.stage = BillStages.IN_COMMITTEE
                self.stage_date = kp.date
        except KnessetProposal.DoesNotExist:
            pass
        try:
            gp = self.gov_proposal
            if not (self.stage_date) or self.stage_date < gp.date:
                self.stage = BillStages.IN_COMMITTEE
                self.stage_date = gp.date
        except GovProposal.DoesNotExist:
            pass
        for cm in self.first_committee_meetings.all():
            if not (self.stage_date) or self.stage_date < cm.date:
                # if it was converted to discussion, seeing it in
                # a cm doesn't mean much.
                if self.stage != BillStages.CONVERTED_TO_DISCUSSION:
                    self.stage = BillStages.IN_COMMITTEE
                    self.stage_date = cm.date
        for v in self.pre_votes.all():
            if not (self.stage_date) or self.stage_date < v.time.date():
                for h in CONVERT_TO_DISCUSSION_HEADERS:
                    if v.title.find(h) >= 0:
                        self.stage = BillStages.CONVERTED_TO_DISCUSSION  # converted to discussion
                        self.stage_date = v.time.date()
        for v in self.pre_votes.all():
            if not (self.stage_date) or self.stage_date < v.time.date():
                if v.for_votes_count > v.against_votes_count:
                    self.stage = BillStages.PRE_APPROVED
                else:
                    self.stage = BillStages.FAILED_PRE_APPROVAL
                self.stage_date = v.time.date()
        for pp in self.proposals.all():
            if not (self.stage_date) or self.stage_date < pp.date:
                self.stage = BillStages.PROPOSED
                self.stage_date = pp.date
        self.save()
        self.generate_activity_stream()

    def generate_activity_stream(self):
        ''' create an activity stream based on the data stored in self '''

        Action.objects.stream_for_actor(self).delete()
        ps = list(self.proposals.all())
        try:
            ps.append(self.gov_proposal)
        except GovProposal.DoesNotExist:
            pass

        for p in ps:
            action.send(self, verb='was-proposed', target=p,
                        timestamp=p.date, description=p.title)

        try:
            p = self.knesset_proposal
            action.send(self, verb='was-knesset-proposed', target=p,
                        timestamp=p.date, description=p.title)
        except KnessetProposal.DoesNotExist:
            pass

        for v in self.pre_votes.all():
            discussion = False
            for h in CONVERT_TO_DISCUSSION_HEADERS:
                if v.title.find(h) >= 0:  # converted to discussion
                    discussion = True
            if discussion:
                action.send(self, verb='was-converted-to-discussion', target=v,
                            timestamp=v.time)
            else:
                action.send(self, verb='was-pre-voted', target=v,
                            timestamp=v.time, description=v.passed)

        if self.first_vote:
            action.send(self, verb='was-first-voted', target=self.first_vote,
                        timestamp=self.first_vote.time, description=self.first_vote.passed)

        if self.approval_vote:
            action.send(self, verb='was-approval-voted', target=self.approval_vote,
                        timestamp=self.approval_vote.time, description=self.approval_vote.passed)

        for cm in self.first_committee_meetings.all():
            action.send(self, verb='was-discussed-1', target=cm,
                        timestamp=cm.date, description=cm.committee.name)

        for cm in self.second_committee_meetings.all():
            action.send(self, verb='was-discussed-2', target=cm,
                        timestamp=cm.date, description=cm.committee.name)

        for g in self.gov_decisions.all():
            action.send(self, verb='was-voted-on-gov', target=g,
                        timestamp=g.date, description=str(g.stand))

    @property
    def frozen(self):
        return self.stage == u'0'

    @property
    def latest_private_proposal(self):
        return self.proposals.order_by('-date').first()

    @property
    def stage_id(self):
        try:
            return (key for key, value in BILL_STAGES.items() if value == self.stage).next()
        except StopIteration:
            return BILL_STAGES['UNKNOWN']

    def is_past_stage(self, lookup_stage_id):
        res = False
        my_stage_id = self.stage_id
        for iter_stage_id in BILL_STAGES.keys():
            if lookup_stage_id == iter_stage_id:
                res = True
            if my_stage_id == iter_stage_id:
                break
        return res


def get_n_debated_bills(n=None):
    """Returns n random bills that have an active debate in the site.
    if n is None, it returns all of them."""

    bill_votes = [x['object_id'] for x in voting.models.Vote.objects.get_popular(Bill)]
    if not bill_votes:
        return None

    bills = Bill.objects.filter(pk__in=bill_votes,
                                stage_date__gt=Knesset.objects.current_knesset().start_date)
    if (n is not None) and (n < len(bill_votes)):
        bills = random.sample(bills, n)
    return bills


def get_debated_bills():
    """
    Returns 3 random bills that have an active debate in the site
    """
    debated_bills = cache.get('debated_bills')
    if not debated_bills:
        debated_bills = get_n_debated_bills(3)
        cache.set('debated_bills', debated_bills, settings.LONG_CACHE_TIME)
    return debated_bills
