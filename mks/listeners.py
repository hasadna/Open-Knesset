#encoding: utf-8
from django.db.models.signals import post_save, post_delete
from planet.models import Feed, Post
from actstream import action
from knesset.utils import cannonize, disable_for_loaddata
from links.models import Link, LinkType
from models import Member, Knesset
from django.dispatch import receiver

import logging
_logger = logging.getLogger("open-knesset.mks.listeners")

@receiver(post_save, sender=Feed)
@disable_for_loaddata
def connect_feed(sender, created, instance, **kwargs):
    if created:
        t = cannonize(instance.title)
        rss_type, _  = LinkType.objects.get_or_create(title='רסס')
        for m in Member.objects.all():
            if t.rfind(cannonize(m.name)) != -1:
                Link.objects.create(url=instance.url, title = instance.title,
                                    content_object=m, link_type=rss_type)
                _logger.info(u'connected feed to {}'.format(m))
                return

@receiver(post_save, sender=Post)
@disable_for_loaddata
def record_post_action(sender, created, instance, **kwargs):
    if created:
        try:
            link, _ = Link.objects.get_or_create(url=instance.feed.url)
        except Link.MultipleObjectsReturned,e:
            _logger.warn('Multiple feeds: {}'.format(e))
            link = Link.objects.filter(url=instance.feed.url)[0]
        member  = link.content_object
        action.send(member, verb='posted',
                    target = instance,
                    timestamp=instance.date_modified or instance.date_created)

@receiver([post_save, post_delete], sender=Knesset)
def reset_current_knesset(sender, instance, **kwargs):
    """Make sure current knesset is cleared upon changes to Knesset"""
    Knesset.objects._current_knesset = None
