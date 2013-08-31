from django import template
from django.conf import settings
from django.core.cache import cache
from links.models import Link

register = template.Library()


@register.inclusion_tag('links/_object_links.html')
def object_links(obj):
    l = Link.objects.for_model(obj)
    return {'links': l, 'MEDIA_URL': settings.MEDIA_URL}


@register.inclusion_tag('links/_object_icon_links.html')
def object_icon_links(obj):
    "Display links as icons, to match the new design"
    key = "%s.%s.%s" % (obj._meta.app_label, obj._meta.module_name, obj.pk)
    l = cache.get(key, None)  # look in the cache first
    if l is None:  # if not found in cache
        l = Link.objects.for_model(obj)  # get it from db
        cache.set(key, l, settings.LONG_CACHE_TIME)  # and save to cache
    return {'links': l}
