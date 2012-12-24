from django.contrib.syndication.views import Feed
from django.utils.translation import ugettext as _
from actstream.models import Action

def main_actions():
    """
    Actions used for main view latests actions and for /feeds/main
    """
    return Action.objects.all().filter(verb__in=['comment-added','annotated']).order_by('-timestamp')

class MainActionsFeed(Feed):
    '''
    A feed for each action presented on the main view.
    '''

    def title(self):
        return _('Main activity feed')

    def link(self):
        return '/'

    def description(self):
        return _('Main activity feed for the whole site, same as presented on the main page')

    def items(self):
        return main_actions()[:20]

    def item_title(self, item):
        title = _(item.verb)
        if item.description:
            title += u' %s' % _(item.description)
        return title

    def item_description(self, item):
        target = item.target
        return target

    def item_link(self, item):
        target = item.target
        # if not target:
        #     print item
        try:
            return getattr(target, 'url')
        except:
            return target.get_absolute_url()

