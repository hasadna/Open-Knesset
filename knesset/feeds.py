from django.utils.translation import ugettext as _
from django.contrib.syndication.views import Feed
from django.contrib.comments.models import Comment
from django.shortcuts import get_object_or_404
from annotatetext.models import Annotation
from laws.models import Vote, Bill
from knesset.utils import main_actions

class Comments(Feed):
    title = "%s | %s" %(_("Open Knesset"), _("Comments feed"))
    link = "/comments/"
    description = "Comments on Open Knesset website"

    def items(self):
        return Comment.objects.order_by('-submit_date')[:20]

    def item_description(self, item):
        n = 1000
        if len(item.comment) > n:
            return "%s: %s..." % (item.name, item.comment[:n])
        return "%s: %s" % (item.name, item.comment)

class Votes(Feed):
    title = "%s | %s" %(_("Open Knesset"), _("Votes feed"))
    link = "/votes/"
    description = "Votes on Open Knesset website"

    def items(self):
        return Vote.objects.order_by('-time')[:20]


class Bills(Feed):
    title = "%s | %s" %(_("Open Knesset"), _("Bills feed"))
    link = "/bills/"
    description = "Bills on Open Knesset website"

    def get_object (self, request, *args, **kwargs):
        stages = request.GET.get('stages', False)
        #TODO: there's probably a re-entrancy issue with self.stages
        self.stages = stages.split(',') if stages else False
        return super(Bills,self).get_object(request, *args, **kwargs)

    def items(self):
        bills = Bill.objects.order_by('-id')
        if self.stages:
            bills = bills.filter(stage__in = self.stages)
        return bills[:20]


class MainActionsFeed(Feed):
    '''
    A feed for each action presented on the main view.
    '''

    title = _('Main activity feed')
    link = '/'
    description = _('Main activity feed for the whole site, same as presented on the main page')

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
        if not target:
            return '/'
        if hasattr(target, 'get_absolute_url'):
            return target.get_absolute_url()
        if hasattr(target, 'url'):
            return getattr(target, 'url')
        return '/'

class Annotations(Feed):
    title = "%s | %s %s" %(_("Open Knesset"), _("Annotations"), _("feed"))
    link = "/committees/"
    description = "Annotations on Committees Protocols"

    def items(self):
        return Annotation.objects.order_by('-timestamp')[:20]

    def item_title(self, item):
        return "%s: %s" % (unicode(item.flag_value), item.comment)

    def item_description(self, item):
        return '"...%s..."' % item.selection

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.timestamp

    def item_author_name(self, item):
        return item.user.get_full_name()

    
    
