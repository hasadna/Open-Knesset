from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms.fields import IntegerField
from django.dispatch import receiver
from django.db.models.signals import post_save

from mks.models import Member, GENDER_CHOICES
from links.models import Link
from .managers import PersonManager

from django.contrib.auth.models import User


class Title(models.Model):
    name = models.CharField(max_length=64)

    def __unicode__(self):
        return self.name


class PersonAlias(models.Model):
    name = models.CharField(max_length=64)
    person = models.ForeignKey('Person', related_name='aliases')

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
    img_url = models.URLField(blank=True)
    phone = models.CharField(blank=True, null=True, max_length=20)
    fax = models.CharField(blank=True, null=True, max_length=20)
    email = models.EmailField(blank=True, null=True)
    family_status = models.CharField(blank=True, null=True, max_length=10)
    number_of_children = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(blank=True, null=True, max_length=100)
    date_of_death = models.DateField(blank=True, null=True)
    year_of_aliyah = models.IntegerField(blank=True, null=True)
    place_of_residence = models.CharField(blank=True, null=True, max_length=100,
                                          help_text=_('an accurate place of residence (for example, an address'))
    area_of_residence = models.CharField(blank=True, null=True, max_length=100,
                                         help_text=_('a general area of residence (for example, "the negev"'))
    place_of_residence_lat = models.CharField(blank=True, null=True, max_length=16)
    place_of_residence_lon = models.CharField(blank=True, null=True, max_length=16)
    residence_centrality = models.IntegerField(blank=True, null=True)
    residence_economy = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    calendar_url = models.CharField(blank=True, null=True, max_length=1024)
    calendar_sync_token = models.CharField(blank=True, null=True, max_length=1024)
    user = models.ForeignKey('auth.User', blank=True, null=True)

    objects = PersonManager()

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
            return reverse('person-detail', kwargs={'pk': self.id})

    def number_of_meetings(self):
        return self.protocol_parts.values('meeting').distinct().count()

    def number_of_committees(self):
        return self.protocol_parts.values('meeting__committee').distinct().count()

    def copy(self, mk=mk):
        """ copy relelvant mk's data to self """
        roles = other.mk.all()
        for role in roles:
            role.pk = None
            role.person = self
            role.save()
        links = Link.objects.for_model(mk)
        for link in links:
            link.pk = None
            link.content_object = self
            link.save()
        for field in mk._meta.fields:
            if field in ['id']:
                continue
            field_name = field.get_attname()
            val = getattr(mk, field_name)
            if val and hasattr(self, field_name):
                # update only empty fields
                if not getattr(self, field_name):
                    setattr(self, field_name, val)

    def merge(self, other):
        """make other into an alias of self"""
        roles = other.roles.all()
        links = Link.objects.for_model(other)
        parts = other.protocol_parts.all()
        external_info = other.external_info.all()
        external_relation = other.external_relation.all()
        if other.mk:
            if self.mk and self.mk != other.mk:
                # something is wrong, we are trying to merge two persons with non matching MKs
                raise ValidationError('Trying to merge persons with non matching MKs')
            self.mk = other.mk
            roles = chain(roles, other.mk.roles.all())
            links = chain(links, other.mk.links.all())
        for title in other.titles.all():
            self.titles.add(title)
        for role in roles:
            role.person = self
            role.save()
        for link in links:
            link.content_object = self
            link.save()
        for part in parts:
            part.speaker = self
            part.save()
        for i in external_info:
            i.person = self
            i.save()
        for i in external_relation:
            i.person = self
            i.save()

        # copy all the model's fields

        for field in self._meta.fields:
            if field in ['id']:
                continue
            field_name = field.get_attname()
            val = getattr(other, field_name)
            if val and not getattr(self, field_name):
                setattr(self, field_name, val)
        if self.name != other.name:
            (pa, created) = PersonAlias.objects.get_or_create(name=other.name, person=self)
        other.delete()
        self.save()

    def create_user(self, username=None, password=None):
        """Create an Auth User for this person - so she can login to django"""
        name_split = self.name.split(' ')
        user = User(
            username=username if username is not None else self.email.split('@')[0],
            first_name=name_split[0],
            last_name=' '.join(name_split[1:]) if len(name_split) > 1 else '',
            email=self.email
        )
        if password is not None:
            user.set_password(password)
        user.save()
        self.user = user
        self.save()
        return user

    def add_alias(self, alias):
        PersonAlias.objects.get_or_create(name=alias, person=self)

    def del_alias(self, alias):
        PersonAlias.objects.filter(name=alias, person=self).delete()


@receiver(post_save, sender=Member)
def member_post_save(sender, **kwargs):
    instance = kwargs['instance']
    person = Person.objects.get_or_create(mk=instance)[0]
    for field in instance._meta.fields:
        if field.name != 'id' and hasattr(person, field.name):
            setattr(person, field.name, getattr(instance, field.name))

    person.save()


class Role(models.Model):
    start_date = models.DateField(null=True)
    end_date = models.DateField(blank=True, null=True)
    text = models.CharField(blank=True, null=True, max_length=1024)
    org = models.TextField(blank=True, null=True)
    person = models.ForeignKey(Person, related_name='roles')

    def __unicode__(self):
        return _('{person} serverd as {text} in {org} from {start_date} to {end_date}').format(
            person=self.person, text=self.text, org=self.org,
            start_date=self.start_date, end_date=self.end_date)


class ProcessedProtocolPart(models.Model):
    """This model is used to keep track of protocol parts already searched for creating persons.
       There should be only 1 record in it, with the max id of a protocol part searched"""
    protocol_part_id = models.IntegerField()


class ExternalData(models.Model):
    ''' an abstract class for extranl data meta data '''
    source = models.CharField(max_length=64)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class ExternalInfo(ExternalData):
    ''' a model for a text key and its value tied to a person '''
    person = models.ForeignKey(Person, related_name='external_info')
    key = models.CharField(max_length=64)
    value = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return u"{} - {}: {}".format(self.person, self.key, self.value)


class ExternalRelation(ExternalData):
    ''' a relationship between two persons '''
    person = models.ForeignKey(Person, related_name='external_relation')
    relationship = models.CharField(max_length=64)
    with_person = models.ForeignKey(Person, null=True, blank=True)

    def __unicode__(self):
        return u"{} - {}: {}".format(self.person, self.relationship,
                                     self.with_person)
