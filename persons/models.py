from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms.fields import IntegerField

GENDER_CHOICES = (
    (u'M', _('Male')),
    (u'F', _('Female')),
)

class Title(models.Model):
    name = models.CharField(max_length=64)

    def __unicode__(self):
        return self.name

class PersonAlias(models.Model):
    name = models.CharField(max_length=64)
    person = models.ForeignKey('Person')

    def __unicode__(self):
        return "%s -> %s" % (self.name, self.person.name)

GENDER_CHOICES = (
    (u'M', _('Male')),
    (u'F', _('Female')),
)

class Person(models.Model):
    name = models.CharField(max_length=64)
    mk = models.ForeignKey('mks.Member', blank=True, null=True, related_name='person')
    titles = models.ManyToManyField(Title, blank=True, null=True, related_name='persons')
    # TODO: change to an ImageField
    img_url = models.URLField(blank=True, verify_exists=False)
    phone = models.CharField(blank=True, null=True, max_length=20)
    fax = models.CharField(blank=True, null=True, max_length=20)
    email = models.EmailField(blank=True, null=True)
    family_status = models.CharField(blank=True, null=True,max_length=10)
    number_of_children = models.IntegerField(blank=True, null=True)
    date_of_birth  = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(blank=True, null=True, max_length=100)
    date_of_death  = models.DateField(blank=True, null=True)
    year_of_aliyah = models.IntegerField(blank=True, null=True)
    place_of_residence = models.CharField(blank=True, null=True, max_length=100, help_text=_('an accurate place of residence (for example, an address'))
    area_of_residence = models.CharField(blank=True, null=True, max_length=100, help_text = _('a general area of residence (for example, "the negev"'))
    place_of_residence_lat = models.CharField(blank=True, null=True, max_length=16)
    place_of_residence_lon = models.CharField(blank=True, null=True, max_length=16)
    residence_centrality = models.IntegerField(blank=True, null=True)
    residence_economy = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _('Person')
        verbose_name_plural = _('Persons')

    def get_absolute_url(self):
        if self.mk:
            return self.mk.get_absolute_url()
        else:
            return reverse('person-detail', kwargs={'pk':self.id})

    def number_of_meetings(self):
        return self.protocol_parts.values('meeting').distinct().count()

    def number_of_committees(self):
        return self.protocol_parts.values('meeting__committee').distinct().count()

    def merge(self, other):
        """make other into an alias of self"""
        if other.mk:
            if self.mk and self.mk != other.mk:
                # something is wrong, we are trying to merge two persons with non matching MKs
                raise ValidationError('Trying to merge persons with non matching MKs')
            self.mk = other.mk
        for title in other.titles.all():
            self.titles.add(title)
        for role in other.roles.all():
            role.person = self
            role.save()
        (pa,created) = PersonAlias.objects.get_or_create(name=other.name,person=self)
        if created:
            pa.save()
        for part in other.protocol_parts.all():
            part.speaker = self
            part.save()
        other.delete()
        self.save()

class Role(models.Model):
    text = models.CharField(blank=True,null=True, max_length=1024)
    person = models.ForeignKey(Person, related_name='roles')

    def __unicode__(self):
        return self.text

class ProcessedProtocolPart(models.Model):
    """This model is used to keep track of protocol parts already searched for creating persons.
       There should be only 1 record in it, with the max id of a protocol part searched"""
    protocol_part_id = models.IntegerField()
