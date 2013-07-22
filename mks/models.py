#encoding: utf-8
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import models
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Q, Max
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User
from planet.models import Blog
from knesset.utils import cannonize
from links.models import Link
import difflib
from mks.managers import (
    BetterManager, KnessetManager, CurrentKnessetMembersManager,
    CurrentKnessetPartyManager)

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
        return _(u'Knesset %(number)d') % {'number': self.number}

    def get_absolute_url(self):
        return reverse('parties-members-list', kwargs={'pk': self.number})


class Party(models.Model):
    name = models.CharField(max_length=64)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_coalition = models.BooleanField(default=False)
    number_of_members = models.IntegerField(blank=True, null=True)
    number_of_seats = models.IntegerField(blank=True, null=True)
    knesset = models.ForeignKey(Knesset, related_name='parties', db_index=True,
                                null=True, blank=True)

    logo = models.ImageField(blank=True,null=True,upload_to='partyLogos')

    objects = BetterManager()
    current_knesset = CurrentKnessetPartyManager()

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
            if (not membership.start_date or membership.start_date <= date) and\
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


class Membership(models.Model):
    member = models.ForeignKey('Member')
    party = models.ForeignKey('Party')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    position = models.PositiveIntegerField(blank=True, default=999)

    def __unicode__(self):
        return "%s-%s (%s-%s)" % (self.member.name, self.party.name, str(self.start_date), str(self.end_date))


class MemberAltname(models.Model):
    member = models.ForeignKey('Member')
    name = models.CharField(max_length=64)


class Member(models.Model):
    name = models.CharField(max_length=64)
    parties = models.ManyToManyField(
        Party, related_name='all_members', through='Membership')
    current_party = models.ForeignKey(
        Party, related_name='members', blank=True, null=True)
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
    place_of_residence = models.CharField(blank=True, null=True, max_length=100, help_text=_('an accurate place of residence (for example, an address'))
    area_of_residence = models.CharField(blank=True, null=True, max_length=100, help_text=_('a general area of residence (for example, "the negev"'))
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

    objects = BetterManager()
    current_knesset = CurrentKnessetMembersManager()

    class Meta:
        ordering = ['name']
        verbose_name = _('Member')
        verbose_name_plural = _('Members')

    def __unicode__(self):
        return self.name

    def save(self, **kwargs):
        self.recalc_average_monthly_committee_presence()
        super(Member, self).save(**kwargs)

    def average_votes_per_month(self):
        return self.voting_statistics.average_votes_per_month()

    def is_female(self):
        return self.gender == 'F'

    def title(self):
        return self.name

    def name_with_dashes(self):
        return self.name.replace(' - ', ' ').replace("'", "").replace(u"”", '').replace("`", "").replace("(", "").replace(")", "").replace(u'\xa0', ' ').replace(' ', '-')

    def Party(self):
        return self.parties.all().order_by('-membership__start_date')[0]

    def PartiesString(self):
        return ", ".join([p.NameWithLink() for p in self.parties.all().order_by('membership__start_date')])
    PartiesString.allow_tags = True

    def party_at(self, date):
        """Returns the party this memeber was at given date
        """
        memberships = Membership.objects.filter(member=self)
        for membership in memberships:
            if (not membership.start_date or membership.start_date <= date) and\
               (not membership.end_date or membership.end_date >= date):
                return membership.party
        return None

    def TotalVotesCount(self):
        return self.votes.exclude(voteaction__type='no-vote').count()

    def for_votes(self):
        return self.votes.filter(voteaction__type='for')

    def ForVotesCount(self):
        return self.for_votes().count()

    def against_votes(self):
        return self.votes.filter(voteaction__type='against')

    def AgainstVotesCount(self):
        return self.against_votes().count()

    def abstain_votes(self):
        return self.votes.filter(voteaction__type='abstain')

    def AbstainVotesCount(self):
        return self.abstain_votes().count()

    def no_votes(self):
        return self.votes.filter(voteaction__type='no-vote')

    def NoVotesCount(self):
        return self.no_votes().count()

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
        """returns the number of days this MK has been serving in the current knesset"""
        if not self.start_date:
            return 0
        if self.is_current:
            return (date.today() - self.start_date).days
        else:
            try:
                return (self.end_date - self.start_date).days
            except TypeError:
                logger.warn(
                    'MK %d is not current, but missing end or start date' %
                    self.id)
                return None

    def average_weekly_presence(self):
        hours = WeeklyPresence.objects.filter(
            member=self).values_list('hours', flat=True)
        if len(hours):
            return round(sum(hours) / len(hours), 1)
        else:
            return None

    def committee_meetings_count(self):
        return self.committee_meetings.count()

    def committee_meetings_per_month(self):
        service_time = self.service_time()
        if not service_time or not self.id:
            return 0
        return round(self.committee_meetings.count() * 30.0 / self.service_time(), 2)

    @models.permalink
    def get_absolute_url(self):
        return ('member-detail-with-slug', [str(self.id), self.name_with_dashes()])

    def NameWithLink(self):
        return '<a href="%s">%s</a>' % (self.get_absolute_url(), self.name)
    NameWithLink.allow_tags = True

    @property
    def get_role(self):
        if self.current_role_descriptions:
            return self.current_role_descriptions
        if self.is_current:
            if self.is_female():
                if self.current_party.is_coalition:
                    return ugettext('Coalition Member (female)')
                else:
                    return ugettext('Opposition Member (female)')
            else:
                if self.current_party.is_coalition:
                    return ugettext('Coalition Member (male)')
                else:
                    return ugettext('Opposition Member (male)')

        if self.is_female():
            return ugettext('Past Member (female)')
        else:
            return ugettext('Past Member (male)')

    @property
    def roles(self):
        """Roles list (splitted by pipe)"""

        return [x.strip() for x in self.get_role.split('|')]

	@property
	def committees(self):
		"""Committee list (splitted by comma)"""

		return [x.strip() for x in self.committees.split(',')]

    @property
    def is_minister(self):
        """Check if one of the roles starts with minister"""

        # TODO Once we have roles table change this
        minister = ugettext('Minister')
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
        self.bills_stats_proposed = self.bills.count()
        self.bills_stats_pre = self.bills.filter(
            stage__in=['2', '3', '4', '5', '6']).count()
        self.bills_stats_first = self.bills.filter(
            stage__in=['4', '5', '6']).count()
        self.bills_stats_approved = self.bills.filter(stage='6').count()
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


class WeeklyPresence(models.Model):
    member = models.ForeignKey('Member')
    date = models.DateField(blank=True, null=True)  # contains the date of the begining of the relevant week (actually monday)
    hours = models.FloatField(
        blank=True)  # number of hours this member was present during this week

    def __unicode__(self):
        return "%s %s %.1f" % (self.member.name, str(self.date), self.hours)

    def save(self, **kwargs):
        super(WeeklyPresence, self).save(**kwargs)
        self.member.recalc_average_weekly_presence_hours()

# force signal connections
from listeners import *
