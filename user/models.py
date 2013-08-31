#encoding: utf-8
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from actstream.models import Follow

from mks.models import Party, Member
from persons.models import GENDER_CHOICES
from laws.models import Bill
from agendas.models import Agenda
from committees.models import CommitteeMeeting,Topic


NOTIFICATION_PERIOD_CHOICES = (
    (u'N', _('No Email')),
    (u'D', _('Daily')),
    (u'W', _('Weekly')),
)

class UserProfile(models.Model):
    '''
    This model is extending the builtin user model.
    The extension includes a list of followed objects,
    such as parties, members and agendas.

    >>> import datetime
    >>> daonb = User.objects.create(username='daonb')
    >>> profile = daonb.get_profile()
    >>> legalize = Party.objects.create(name='legalize')
    >>> follow(daonb, legalize)
    <Follow: daonb -> legalize>
    >>> legalize == daonb.get_profile().parties[0]
    True
    >>> dbg = Member.objects.create(name='david ben gurion', start_date=datetime.date(2010,1,1))
    >>> follow(daonb, dbg)
    <Follow: daonb -> david ben gurion>
    >>> dbg == daonb.get_profile().members[0]
    True

    '''

    user = models.ForeignKey(User, unique=True, related_name='profiles')
    public_profile = models.BooleanField(default=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    description = models.TextField(null=True,blank=True)
    email_notification = models.CharField(max_length=1, choices=NOTIFICATION_PERIOD_CHOICES, blank=True, null=True)
    party = models.ForeignKey('mks.Party', null=True, blank=True)

    def get_actors(self, model, *related):
        lst = Follow.objects.filter(user=self.user,
                       content_type=ContentType.objects.get_for_model(model))
        if related:
            lst = lst.prefetch_related(*related)
        return [x.actor for x in lst]
    
    @property
    def members(self):
        return self.get_actors(Member, 'actor')

    @property
    def bills(self):
        return self.get_actors(Bill, 'actor')

    @property
    def parties(self):
        #TODO: ther has to be a faster way
        return self.get_actors(Party)

    @property
    def agendas(self):
        return self.get_actors(Agenda, 'actor', 'actor__agendavotes')

    @property
    def meetings(self):
        return self.get_actors(CommitteeMeeting, 'actor')

    @property
    def topics(self):
        return self.get_actors(Topic, 'actor')


    def get_badges(self):
        return self.badges.all()

    @models.permalink
    def get_absolute_url(self):
        return ('public-profile', (), {'pk': self.user.id})

    def has(self, badge_type):
        return self.badges.filter(badge_type=badge_type).count()>0

    def __unicode__(self):
        return self.user.get_full_name() or self.user.username

def handle_user_save(sender, created, instance, **kwargs):
    if created and instance._state.db=='default':
        UserProfile.objects.create(user=instance)
post_save.connect(handle_user_save, sender=User)
