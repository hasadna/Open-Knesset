from django import template

register = template.Library()


# TODO: Currently this is a complete copy of selector(which copies paginator I think) tag with another query param
# Hopefully this could refactored using a base class (something like django-classy-tags) to be just different by param
@register.inclusion_tag('laws/_paginator.html')
def knesset_selection(page_obj, paginator, request):
    """ includes links to previous/next page, and other pages if needed """
    base_query = '&'.join(["%s=%s" % (k, v) for (k, v) in request.GET.items() if k != 'knesset'])
    if paginator.num_pages <= 10:
        show_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in paginator.object_list]
        show_pages[page_obj.number][2] = True
    else:
        if page_obj.number <= 5:
            show_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in
                          paginator.object_list[:page_obj.number + 2]]
            last_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in
                          paginator.object_list[paginator.num_pages - 2:paginator.num_pages]]
        elif page_obj.number >= paginator.num_pages - 5:
            show_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in
                          paginator.object_list[page_obj.number - 4:paginator.num_pages]]
            first_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in paginator.object_list[:2]]
        else:
            first_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in paginator.object_list[:2]]
            last_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in
                          paginator.object_list[paginator.num_pages - 2:paginator.num_pages]]
            show_pages = [[x, "?%s&knesset=%d" % (base_query, x), False] for x in
                          paginator.object_list[page_obj.number - 3:page_obj.number + 2]]
        current_page = paginator.object_list[page_obj.number]
        for i in show_pages:
            if i[0] == current_page:
                i[2] = True
    # TODO this is an anti pattern in so many ways... should refactor this
    return locals()
