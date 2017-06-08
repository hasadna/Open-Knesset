# encoding: utf-8
from datetime import date

import itertools

import waffle
from dateutil.relativedelta import relativedelta
from django.db import models
import datetime

from django.core.urlresolvers import reverse
from django.db.models import Q, Max
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from planet.models import Blog

from knesset import utils
from laws.enums import BillStages

from links.models import Link

from mks.managers import (
    PartyManager, KnessetManager, CurrentKnessetMembersManager,
    CurrentKnessetPartyManager, MembershipManager, CurrentKnessetActiveMembersManager, MemberManager)

GENDER_CHOICES = (
    (u'M', _('Male')),
    (u'F', _('Female')),
)


class Correlation(models.Model):
    m1 = models.ForeignKey('Member', related_name='m1')
    m2 = models.ForeignKey('Member', related_name='m2')
    score = models.IntegerField(default=0)
    normalized_score = models.FloatField(null=True)
    not_same_party = models.NullBooleanField()

    def __unicode__(self):
        return "%s - %s - %.0f" % (self.m1.name, self.m2.name, self.normalized_score)


class CoalitionMembership(models.Model):
    party = models.ForeignKey('Party',
                              related_name='coalition_memberships')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ('party', 'start_date')

    def __unicode__(self):
        return "%s %s %s" % ((self.party.name,
                              self.start_date or "",
                              self.end_date or ""))


class Knesset(models.Model):
    number = models.IntegerField(_('Knesset number'), primary_key=True)
    start_date = models.DateField(_('Start date'), blank=True, null=True)
    end_date = models.DateField(_('End date'), blank=True, null=True)

    objects = KnessetManager()

    def __unicode__(self):
        return self.name

    @property
    def name(self):
        return _(u'Knesset %(number)d') % {'number': self.number}

    def get_absolute_url(self):
        return reverse('parties-members-list', kwargs={'pk': self.number})


class Party(models.Model):
    name = models.CharField(max_length=64)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_coalition = models.BooleanField(default=False)
    number_of_members = models.IntegerField(blank=True, null=True)
    number_of_seats = models.IntegerField(blank=True, null=True, help_text='Last known number of seats')
    knesset = models.ForeignKey(Knesset, related_name='parties', db_index=True,
                                null=True, blank=True)

    logo = models.ImageField(blank=True, null=True, upload_to='partyLogos')

    objects = PartyManager()
    current_knesset = CurrentKnessetPartyManager()

    split_from = models.ForeignKey('self', blank=True, null=True)

    class Meta:
        verbose_name = _('Party')
        verbose_name_plural = _('Parties')
        ordering = ('-number_of_seats',)
        unique_together = ('knesset', 'name')

    @property
    def uri_template(self):
        # TODO: use the Site's url from django.contrib.site
        return "%s/api/party/%s/htmldiv/" % ('', self.id)

    def __unicode__(self):
        if self.is_current:
            return self.name

        return _(u'%(name)s in Knesset %(number)d') % {
            'name': self.name,
            'number': self.knesset.number if self.knesset else 0
        }

    def current_members(self):
        # for current knesset, we want to display by selecting is_current,
        # for older ones, it's not relevant
        if self.knesset == Knesset.objects.current_knesset():
            return self.members.filter(
                is_current=True).order_by('current_position')
        else:
            return self.all_members.order_by('current_position')

    def past_members(self):
        return self.members.filter(is_current=False)

    def name_with_dashes(self):
        return self.name.replace("'", '"').replace(' ', '-')

    def Url(self):
        return "/admin/simple/party/%d" % self.id

    def NameWithLink(self):
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.name)

    NameWithLink.allow_tags = True

    def MembersString(self):
        return ", ".join([m.NameWithLink() for m in self.members.all().order_by('name')])

    MembersString.allow_tags = True

    def member_list(self):
        return self.members.all()

    def is_coalition_at(self, date):
        """Returns true is this party was a part of the coalition at the given
        date"""
        memberships = CoalitionMembership.objects.filter(party=self)
        for membership in memberships:
            if (not membership.start_date or membership.start_date <= date) and \
                    (not membership.end_date or membership.end_date >= date):
                return True
        return False

    @models.permalink
    def get_absolute_url(self):
        return ('party-detail', [str(self.id)])

    def get_affiliation(self):
        return _('Coalition') if self.is_coalition else _('Opposition')

    @property
    def is_current(self):
        return self.knesset == Knesset.objects.current_knesset()


class PartySeats(models.Model):
    party = models.ForeignKey(Party)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    number_of_seats = models.IntegerField(blank=True, null=True)


class Membership(models.Model):
    member = models.ForeignKey('Member')
    party = models.ForeignKey('Party')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    position = models.PositiveIntegerField(blank=True, default=999)

    objects = MembershipManager()

    def __unicode__(self):
        return "%s-%s (%s-%s)" % (self.member.name, self.party.name, str(self.start_date), str(self.end_date))


class MemberAltname(models.Model):
    member = models.ForeignKey('Member')
    name = models.CharField(max_length=64)

    def save(self, **kwargs):
        super(MemberAltname, self).save(**kwargs)
        [person.add_alias(self.name) for person in self.member.person.all()]

    def delete(self, **kwargs):
        persons = list(self.member.person.all())
        name = self.name
        super(MemberAltname, self).delete(**kwargs)
        [person.del_alias(name) for person in persons]


class Member(models.Model):
    id = models.IntegerField(primary_key=True,
                             help_text="Pay attention that the value of this field must correspond to the official Knesset member id")
    name = models.CharField(max_length=64)
    parties = models.ManyToManyField(
        'Party', related_name='all_members', through='Membership')
    current_party = models.ForeignKey(
        'Party', related_name='members', blank=True, null=True)
    current_position = models.PositiveIntegerField(blank=True, default=999)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    img_url = models.URLField(blank=True)
    phone = models.CharField(blank=True, null=True, max_length=20)
    fax = models.CharField(blank=True, null=True, max_length=20)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    family_status = models.CharField(blank=True, null=True, max_length=10)
    number_of_children = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(blank=True, null=True, max_length=100)
    date_of_death = models.DateField(blank=True, null=True)
    year_of_aliyah = models.IntegerField(blank=True, null=True)
    is_current = models.BooleanField(default=True, db_index=True)
    blog = models.OneToOneField(Blog, blank=True, null=True)
    place_of_residence = models.CharField(blank=True, null=True, max_length=100,
                                          help_text=_('an accurate place of residence (for example, an address'))
    area_of_residence = models.CharField(blank=True, null=True, max_length=100,
                                         help_text=_('a general area of residence (for example, "the negev"'))
    place_of_residence_lat = models.CharField(
        blank=True, null=True, max_length=16)
    place_of_residence_lon = models.CharField(
        blank=True, null=True, max_length=16)
    residence_centrality = models.IntegerField(blank=True, null=True)
    residence_economy = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    current_role_descriptions = models.CharField(
        blank=True, null=True, max_length=1024)

    bills_stats_proposed = models.IntegerField(default=0)
    bills_stats_pre = models.IntegerField(default=0)
    bills_stats_first = models.IntegerField(default=0)
    bills_stats_approved = models.IntegerField(default=0)

    average_weekly_presence_hours = models.FloatField(null=True, blank=True)
    average_monthly_committee_presence = models.FloatField(null=True, blank=True)

    backlinks_enabled = models.BooleanField(default=True)

    objects = MemberManager()
    current_knesset = CurrentKnessetMembersManager()
    current_members = CurrentKnessetActiveMembersManager()

    class Meta:
        ordering = ['name']
        verbose_name = _('Member')
        verbose_name_plural = _('Members')

    def __unicode__(self):
        return self.name

    def save(self, **kwargs):
        self.recalc_average_monthly_committee_presence()
        if self.id is None:
            try:
                max_id = Member.objects.all().aggregate(Max('id'))['id__max']
                if max_id is None:
                    max_id = 0
            except:
                max_id = 0
            max_id += 1
            self.id = max_id
        super(Member, self).save(**kwargs)

    def average_votes_per_month(self):
        return self.voting_statistics.average_votes_per_month()

    def is_female(self):
        return self.gender == 'F'

    def title(self):
        return self.name

    def name_with_dashes(self):
        return self.name.replace(' - ', ' ').replace("'", "").replace(u"”", '').replace("`", "").replace("(",
                                                                                                         "").replace(
            ")", "").replace(u'\xa0', ' ').replace(' ', '-')

    def Party(self):
        return self.parties.all().order_by('-membership__start_date')[0]

    def PartiesString(self):
        return ", ".join([p.NameWithLink() for p in self.parties.all().order_by('membership__start_date')])

    PartiesString.allow_tags = True

    def party_at(self, date):
        from knesset_data_django.mks.utils import party_at
        return party_at(self, date)

    def for_votes(self):
        return self.votes.filter(voteaction__type='for')

    def against_votes(self):
        return self.votes.filter(voteaction__type='against')

    def abstain_votes(self):
        return self.votes.filter(voteaction__type='abstain')

    def no_votes(self):
        return self.votes.filter(voteaction__type='no-vote')

    def LowestCorrelations(self):
        return Correlation.objects.filter(m1=self.id).order_by('normalized_score')[0:4]

    def HighestCorrelations(self):
        return Correlation.objects.filter(m1=self.id).order_by('-normalized_score')[0:4]

    def CorrelationListToString(self, cl):

        strings = []
        for c in cl:
            if c.m1 == self:
                m = c.m2
            else:
                m = c.m1
            strings.append(
                "%s (%.0f)" % (m.NameWithLink(), 100 * c.normalized_score))
        return ", ".join(strings)

    def service_time(self):
        """returns the number of days this MK has been serving in the current
           knesset
        """
        if not self.start_date:
            return 0
        d = Knesset.objects.current_knesset().start_date
        start_date = max(self.start_date, d)
        if self.is_current:
            end_date = date.today()
        else:
            end_date = self.end_date
            if not end_date:
                logger.warn(
                    'MK %d is not current, but end date is None' %
                    self.id)
                return None
        return (end_date - start_date).days

    def average_weekly_presence(self):
        d = Knesset.objects.current_knesset().start_date
        hours = WeeklyPresence.objects.filter(
            date__gte=d,
            member=self).values_list('hours', flat=True)
        if len(hours):
            return round(sum(hours) / len(hours), 1)
        else:
            return None

    def committee_meetings_per_month(self):

        service_time = self.service_time()
        if not service_time or not self.id:
            return 0
        return round(self.total_meetings_count_current_knesset * 30.0 / service_time, 2)

    def committee_meeting_current_knesset(self):
        d = Knesset.objects.current_knesset().start_date
        return self.committee_meetings.filter(
            date__gte=d)

    @property
    def participated_in_committees_for_current_knesset(self):
        committee_meetings = list(self.committee_meeting_current_knesset())
        committees = set()
        for committee, meetings in itertools.groupby(committee_meetings, lambda x: x.committee.name):
            committees.add(committee)

        return committees

    def total_meetings_count_for_committee(self, committee_name):
        return self.committee_meeting_current_knesset().filter(committee__name=committee_name).count()

    def get_active_committees(self):
        return itertools.chain(self.committees.exclude(hide=True),
                               self.chaired_committees.exclude(hide=True),
                               )

    @property
    def total_meetings_count_current_knesset(self):
        return self.committee_meeting_current_knesset().count()

    @models.permalink
    def get_absolute_url(self):
        return ('member-detail-with-slug',
                [str(self.id), self.name_with_dashes()])

    def get_current_knesset_bills_by_stage_url(self, stage):
        current_knesset = Knesset.objects.current_knesset()
        return utils.reverse_with_query('bill-list',
                                        query_kwargs={'member': self.id, 'knesset_id': current_knesset.number,
                                                      'stage': stage})

    def NameWithLink(self):
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.name)

    NameWithLink.allow_tags = True

    @property
    def get_role(self):
        if self.current_role_descriptions:
            return self.current_role_descriptions
        return self.get_gender_aware_mk_role_description()

    def get_gender_aware_mk_role_description(self):
        if self.is_current:
            if self.is_female():
                if self.current_party.is_coalition:
                    return _('Coalition Member (female)')
                else:
                    return _('Opposition Member (female)')
            else:
                if self.current_party.is_coalition:
                    return _('Coalition Member (male)')
                else:
                    return _('Opposition Member (male)')
        if self.is_female():
            return _('Past Member (female)')
        else:
            return _('Past Member (male)')

    @property
    def roles(self):
        """Roles list (splitted by pipe)"""

        return [x.strip() for x in self.get_role.split('|')]

    @property
    def is_minister(self):
        """Check if one of the roles starts with minister"""

        # TODO Once we have roles table change this
        minister = _('Minister')
        return any(x.startswith(minister) for x in self.roles)

    @property
    def coalition_status(self):
        """Current Coalition/Opposition member, or past member. Good for usage
        with Django's yesno filters

        :returns: True - Coalition, False - Opposition, None: Past member
        """
        if not self.is_current:
            return None

        return self.current_party.is_coalition

    def recalc_bill_statistics(self):
        if waffle.switch_is_active('use_old_statistics'):
            self._calc_bill_statistics_by_bill_stage_date()
        else:
            self._calc_bill_statistics_by_proposal_dates()

    def _calc_bill_statistics_by_proposal_dates(self):
        current_knesset = Knesset.objects.current_knesset()
        knesset_range = current_knesset.start_date, current_knesset.end_date or date.today()
        member_bills = self.bills.get_bills_by_private_proposal_date_for_member(knesset_range, member=self)
        self.bills_stats_proposed = member_bills.count()
        self.bills_stats_pre = member_bills.filter(

            stage__in=[BillStages.PRE_APPROVED, BillStages.IN_COMMITTEE, BillStages.FIRST_VOTE,
                       BillStages.COMMITTEE_CORRECTIONS, BillStages.APPROVED, BillStages.FAILED_FIRST_VOTE,
                       BillStages.FAILED_APPROVAL]).count()
        self.bills_stats_first = member_bills.filter(
            stage__in=[BillStages.FIRST_VOTE, BillStages.COMMITTEE_CORRECTIONS, BillStages.APPROVED,
                       BillStages.FAILED_APPROVAL]).count()
        self.bills_stats_approved = member_bills.filter(
            stage=BillStages.APPROVED).count()
        self.save()

    def _calc_bill_statistics_by_bill_stage_date(self):
        # Deprecated method, here to allow reverting if needed
        d = Knesset.objects.current_knesset().start_date
        self.bills_stats_proposed = self.bills.filter(
            stage_date__gte=d).count()
        self.bills_stats_pre = self.bills.filter(
            stage_date__gte=d,
            stage__in=[BillStages.PRE_APPROVED, BillStages.IN_COMMITTEE, BillStages.FIRST_VOTE,
                       BillStages.COMMITTEE_CORRECTIONS, BillStages.APPROVED, BillStages.FAILED_FIRST_VOTE,
                       BillStages.FAILED_APPROVAL]).count()
        self.bills_stats_first = self.bills.filter(
            stage_date__gte=d,
            stage__in=[BillStages.FIRST_VOTE, BillStages.COMMITTEE_CORRECTIONS, BillStages.APPROVED,
                       BillStages.FAILED_APPROVAL]).count()
        self.bills_stats_approved = self.bills.filter(
            stage_date__gte=d,
            stage=BillStages.APPROVED).count()
        self.save()

    def recalc_average_weekly_presence_hours(self):
        self.average_weekly_presence_hours = self.average_weekly_presence()
        self.save()

    def recalc_average_monthly_committee_presence(self):
        self.average_monthly_committee_presence = self.committee_meetings_per_month()

    @property
    def names(self):
        names = [self.name]
        for altname in self.memberaltname_set.all():
            names.append(altname.name)
        return names

    def get_agendas_values(self):
        from agendas.models import Agenda

        out = {}
        for agenda_id, mks in Agenda.objects.get_mks_values().items():
            try:
                out[agenda_id] = dict(mks)[self.id]
            except KeyError:
                pass
        return out

    @property
    def firstname(self):
        """return the first name of the member"""
        return self.name.split()[0]

    @property
    def highres_img_url(self):
        "Get higher res image for the member"

        # TODO a hack for now, change later for url field
        if not self.img_url:
            return self.img_url

        return self.img_url.replace('-s.jpg', '.jpg')

    @property
    def age(self):
        return relativedelta(date.today(), self.date_of_birth)

    @property
    def awards(self):
        return self.awards_and_convictions.filter(award_type__valence__gt=0)

    @property
    def convictions(self):
        return self.awards_and_convictions.filter(award_type__valence__lt=0)


class WeeklyPresence(models.Model):
    member = models.ForeignKey('Member')
    date = models.DateField(blank=True,
                            null=True)  # contains the date of the begining of the relevant week (actually monday)
    hours = models.FloatField(
        blank=True)  # number of hours this member was present during this week

    def __unicode__(self):
        return "%s %s %.1f" % (self.member.name, str(self.date), self.hours)

    def save(self, **kwargs):
        super(WeeklyPresence, self).save(**kwargs)
        self.member.recalc_average_weekly_presence_hours()


class AwardType(models.Model):
    name = models.CharField(max_length=100)
    valence = models.FloatField(default=0)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return u"%s (%d)" % (self.name, self.valence)


class Award(models.Model):
    award_type = models.ForeignKey('AwardType', related_name='awards')
    member = models.ForeignKey('Member', related_name='awards_and_convictions')
    date_given = models.DateField()
    reference = models.URLField(blank=True, max_length=1000)

    def __unicode__(self):
        return u"%s - %s" % (self.member, self.award_type)

    class Meta:
        ordering = ('-date_given',)


# force signal connections
from listeners import *
