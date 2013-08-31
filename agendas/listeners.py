# encoding: utf-8
import datetime
from django.db.models.signals import post_save, pre_delete, post_delete
from django.contrib.contenttypes.models import ContentType
from actstream import action
from actstream.models import Follow
from knesset.utils import disable_for_loaddata

class Listener():
    fmt_updated = u'agenda {atype} relation updated',   u'relation between agenda "{name}" and {atype} "{title}" was updated'
    fmt_created = u'agenda {atype} ascribed',           u'agenda "{name}" ascribed to {atype} "{title}"'
    fmt_removed = u'agenda {atype} removed',            u'agenda "{name}" removed from {atype} "{title}"'

    def do_send(self, instance, verb, fmt, get=False):
        title = instance.key.full_title if hasattr(instance.key, 'full_title') else instance.key.title
        action.send(instance.agenda, verb=verb.format(atype=self.keyname()),
                    target=(self.key if get else instance),
                    timestamp=datetime.datetime.now(),
                    description=fmt.format(name=instance.agenda.name, title=title, atype=self.keyname()))
        
    @disable_for_loaddata
    def record_ascription_action(self, sender, created, instance, **kwargs):
        verb, fmt = Listener.fmt_created if created else Listener.fmt_updated
        self.do_send(instance, verb, fmt)

    @disable_for_loaddata
    def record_removal_action(self, sender, instance, **kwargs):
        verb, fmt = Listener.fmt_removed
        self.do_send(instance, verb, fmt, True)
        
    def __call__(self, aclass):    
        post_save.connect(self.record_ascription_action, sender=aclass)
        pre_delete.connect(self.record_removal_action, sender=aclass)
        return aclass

    
def Follower(agenda_class):
    @disable_for_loaddata
    def _update_num_followers(sender, instance, **kwargs):
        agenda = instance.actor
        if isinstance(agenda, agenda_class):
            agenda.num_followers = Follow.objects.filter(
                content_type=ContentType.objects.get(app_label="agendas", model="agenda").id,
                object_id=agenda.id).count()
            agenda.save()
    post_delete.connect(_update_num_followers, sender=Follow)
    post_save.connect(_update_num_followers, sender=Follow)
    return agenda_class
