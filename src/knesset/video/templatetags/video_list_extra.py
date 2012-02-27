
from django import template

register = template.Library()

@register.inclusion_tag('video/_video_list_item.html')
def video_list_item(video):
    return {'video': video}

@register.inclusion_tag('video/_paginator.html')
def pagination(page_obj, paginator, request):
    """ includes links to previous/next page, and other pages if needed """
    base_link = '&'.join(["%s=%s" % (k,v) for (k,v) in request.GET.items() if k!='page'])
    if paginator.num_pages <= 10:
        show_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(1, paginator.num_pages+1)]
        show_pages[page_obj.number-1][2] = True
    else:
        if page_obj.number <= 5:
            show_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(1, page_obj.number+3)]
            last_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(paginator.num_pages-1, paginator.num_pages+1)]
        elif page_obj.number >= paginator.num_pages-5:
            show_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(page_obj.number-2, paginator.num_pages+1)]
            first_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(1, 3)]
        else:
            first_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(1, 3)]
            last_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(paginator.num_pages-1, paginator.num_pages+1)]
            show_pages = [[x,"?%s&page=%d"%(base_link,x),False] for x in range(page_obj.number-2, page_obj.number+3)]

        for i in show_pages:
            if i[0]==page_obj.number:
                i[2] = True

    return locals()
