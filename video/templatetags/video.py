from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('video/_video_init.html')
def video_init():
    return {
        # not needed since staticfiles - 'MEDIA_URL':settings.MEDIA_URL
    }

@register.inclusion_tag('video/_video_player.html')
def video_player(width,height,embed_link,image_link):
    embed_link=embed_link if embed_link is not None else ''
    image_link=image_link if image_link is not None else ''
    return {
        'width':width, 'height':height,
        'embed_link':embed_link,
        'image_link':image_link,
    }

@register.inclusion_tag('video/_video_playlist.html')
def video_playlist(videos,playlist_id):
    return {'videos':videos,playlist_id:playlist_id}

@register.inclusion_tag('video/_video_playlist_player.html')
def video_playlist_player(video,playlist_id):
    if video.source_type=='mms-knesset-portal':
        embed_link=''
        link=video.embed_link
    else:
        embed_link=video.embed_link
        link=video.link
    if len(video.small_image_link)>0:
        image_link=video.small_image_link
    elif len(video.image_link)>0:
        image_link=video.image_link
    else:
        image_link=''
    return {
        'embed_link':embed_link,
        'image_link':image_link,
        'title':video.title,
        'description':video.description,
        'link':link,
        'published':video.published,
        'source_type':video.source_type,
        'playlist_id':playlist_id
    }

