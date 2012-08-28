from django.contrib.sitemaps import Sitemap
from tagging.models import Tag
from knesset.mks.models import Member, Party
from knesset.laws.models import Vote, Bill
from knesset.committees.models import Committee,CommitteeMeeting
from knesset.agendas.models import Agenda

class LimitSitemap(Sitemap):
    pass
    # this can be used to automatically paginate sitemaps.
    # must use sections for that. currently using a single file-cached sitemap
    # limit = 2000

class MemberSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Member.objects.all()

class BillSitemap(LimitSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Bill.objects.all()

class PartySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.55

    def items(self):
        return Party.objects.all()

class VoteSitemap(LimitSitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Vote.objects.all()

class CommitteeSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Committee.objects.all()

class CommitteeMeetingSitemap(LimitSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return CommitteeMeeting.objects.all()

class AgendaSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Agenda.objects.all()

class TagSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Tag.objects.all()

class IndexPagesSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0
    def items(self): return ['/', '/vote/', '/member/', '/party/',
                             '/committee/', '/about/', '/bills/',
                             '/agenda/', '/tags/']
    def location(self, obj): return obj

sitemaps = {
    'members': MemberSitemap,
    'bills': BillSitemap,
    'parties': PartySitemap,
    'votes': VoteSitemap,
    'committees': CommitteeSitemap,
    'committees_meetings': CommitteeMeetingSitemap,
    'agendas': AgendaSitemap,
    'index': IndexPagesSitemap,
}

