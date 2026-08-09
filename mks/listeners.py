# encoding: utf-8
from django.db.models.signals import post_save, post_delete
from planet.models import Feed, Post
from actstream import action
from knesset.utils import cannonize, disable_for_loaddata
from links.models import Link, LinkType
from models import Member, Knesset

import logging

logger = logging.getLogger("open-knesset.mks.listeners")


@disable_for_loaddata
def connect_feed(sender, created, instance, **kwargs):
    if created:
        t = cannonize(instance.title)
        rss_type, _ = LinkType.objects.get_or_create(title='רסס')
        for m in Member.objects.all():
            if t.rfind(cannonize(m.name)) != -1:
                Link.objects.create(url=instance.url, title=instance.title,
                                    content_object=m, link_type=rss_type)
                logger.info(u'connected feed to %s' % m)
                return


post_save.connect(connect_feed, sender=Feed)


@disable_for_loaddata
def record_post_action(sender, created, instance, **kwargs):
    if created:
        try:
            link, _ = Link.objects.get_or_create(url=instance.feed.url)
        except Link.MultipleObjectsReturned as e:
            logger.warn('Multiple feeds: %s' % e)
            link = Link.objects.filter(url=instance.feed.url)[0]
        member = link.content_object
        action.send(member, verb='posted',
                    target=instance,
                    timestamp=instance.date_modified or instance.date_created)


post_save.connect(record_post_action, sender=Post)


def reset_current_knesset(sender, instance, **kwargs):
    """Make sure current knesset is cleared upon changes to Knesset"""
    Knesset.objects._current_knesset = None


post_save.connect(reset_current_knesset, sender=Knesset)
post_delete.connect(reset_current_knesset, sender=Knesset)
