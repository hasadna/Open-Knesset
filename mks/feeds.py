from django.contrib.syndication.views import Feed
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from actstream import actor_stream
from models import Member

# some translation strings we need for the feed
TRANSLATE_THIS = ( _('voted'), _('posted'), 
                  _('attended'), _('committee meeting'))

class MemberActivityFeed(Feed):
    '''
    A feed for each member. The feed accepts one optional url parameter *verbs* that
    contains a comma-sperated list of verbs to be included in the feed
    '''

    def get_object (self, request, object_id):
        verbs = request.GET.get('verbs', False)
        self.verbs = verbs.split(',') if verbs else False
        return get_object_or_404(Member, pk=object_id)

    def title(self, member):
        return _('Member activity feed for %s') % member

    def link(self, member):
        return member.get_absolute_url()
    
    def description(self, member):
        return _('Actions of %s, including votes, attended committees and posted articles') % member

    def items(self, member):
        stream = actor_stream(member)
        if stream:
            if self.verbs:
                stream = stream.filter(verb__in = self.verbs)
            return (item for item in stream[:20] if item.target) # remove items with None target, or invalid target
        return []

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

