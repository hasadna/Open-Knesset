from django.db import models
from django.utils.translation import ugettext as _

class CandidateList(models.Model):
    candidates = models.ManyToManyField('persons.Person', blank=True, null=True, through='Candidate')
    name = models.CharField(_('Name'), max_length = 80)
    ballot = models.CharField(_('Ballot'), max_length=4)
    number_of_seats = models.IntegerField(blank=True, null=True)
    surplus_partner = models.ForeignKey('self', blank=True, null=True, 
                help_text=_('The list with which is the surplus votes partner'))
    mpg_html_report = models.TextField(_('MPG report'), blank=True, null=True,
                help_text=_('The MPG report on the list, can use html'))
    img_url = models.URLField(blank=True, verify_exists=False)
    youtube_user = models.CharField(_('YouTube user'), max_length = 80, null=True, blank=True)
    wikipedia_page = models.CharField(_('Wikipedia page'), max_length = 80, null=True, blank=True)
    twitter_account = models.CharField(_('Twitter account'), max_length = 80, null=True, blank=True)
    facebook_url = models.URLField(blank=True, verify_exists=True, null=True)
    platform = models.TextField(_('Platform'), blank=True, null=True)

    def save(self, *args, **kwargs):
        super(CandidateList, self).save()
        if self.surplus_partner:
            self.surplus_partner.surplus_partner = self

    def getHeadName(self):
        return Candidate.objects.get(candidates_list=self, ordinal=1).person.name

    @property
    def member_ids(self):
        ''' return a list of all members id in the party '''
        mks = Candidate.objects.filter(candidates_list=self, person__mk__isnull=False)
        return mks.values_list('person__mk__id', flat=True)

    @models.permalink
    def get_absolute_url(self):
        return ('candidate-list-detail', [self.id])

    def __unicode__(self):
        return self.name


class Party(models.Model):
    name = models.CharField(max_length=64)
    
    def __unicode__(self):
        return self.name


class Candidate(models.Model):
    candidates_list = models.ForeignKey(CandidateList)
    person = models.ForeignKey('persons.Person')
    ordinal = models.IntegerField(_('Ordinal'))
    party = models.ForeignKey(Party, blank=True, null=True)
    votes = models.IntegerField(_('Elected by #'), null=True, blank=True, help_text=_('How many people voted for this person'))

    class Meta:
        ordering = ('ordinal',)

    def __unicode__(self):
        return self.person.name
