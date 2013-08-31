from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _

class LastSent(models.Model):
    user = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType,
                                     verbose_name=_('content type'),
                                     related_name="content_type_set_for_%(class)s")
    object_pk = models.TextField(_('object ID'))
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")
    time = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"{} {} {}".format(self.user.username, self.content_object, self.time)    

