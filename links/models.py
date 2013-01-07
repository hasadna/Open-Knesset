import os

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from managers import LinksManager

link_file_storage = FileSystemStorage(os.path.join(settings.DATA_ROOT, 'link_files_storage'))

_default_linktype = False
def get_default_linktype():
    global _default_linktype
    if not _default_linktype:
        _default_linktype = LinkType.objects.get(title='default')
    return _default_linktype

class LinkType(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('title'))
    image = models.ImageField(upload_to='icons')

    class Meta:
        verbose_name = _('link type')
        verbose_name_plural = _('link types')

    def __unicode__(self):
        return self.title

class Link(models.Model):
    url = models.URLField(verbose_name='URL', max_length=1000,
                          verify_exists=False)
    title = models.CharField(max_length=200, verbose_name=_('title'))
    content_type   = models.ForeignKey(ContentType,
            verbose_name=_('content type'),
            related_name="content_type_set_for_%(class)s")
    object_pk      = models.TextField(_('object ID'))
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")
    link_type = models.ForeignKey(LinkType, default=get_default_linktype, null=True, blank=True)
    active = models.BooleanField(default=True)
    objects = LinksManager()

    class Meta:
        verbose_name = _('link')
        verbose_name_plural = _('links')

    def __unicode__(self):
        return "%s: %s" % (self.title, self.url)

class LinkedFile(models.Model):
    link = models.ForeignKey(Link, null=True, blank=True, default=None)
    sha1 = models.CharField(max_length=1000, null=True)
    last_updated = models.DateTimeField(auto_now=True, null=True)
    link_file = models.FileField(storage=link_file_storage, upload_to='link_files')

class ModelWithLinks():
    ''' This is a mixin to be used by classes that have alot of links '''
    def add_link(self, url, title, link_type=None):
        if not link_type:
            link_type = get_default_linktype()
        Links.objects.create(content_object=self, url=url, title=title,
                             link_type=link_type)
    def get_links(self):
        return Links.objects.filter(active=True, content_object=self)
