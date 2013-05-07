import urllib2, re, logging

from django.core.management.base import NoArgsCommand

from mks.models import Member

logger = logging.getLogger("open-knesset.mks.update_mks_url_img")

class Command(NoArgsCommand):
    help = "update all members url_img from knesset website"

    def handle_noargs(self, **options):
        for member in Member.objects.all():
            mk_id = member.id
            search_url = 'http://www.knesset.gov.il/mk/heb/ShowPic.asp?mk_individual_id_t=%s' % mk_id
            try:
                page = urllib2.urlopen(search_url)
                data = page.read()
                res_url = 'http://www.knesset.gov.il/%s' % (
                    re.search('mk/images/members/.*?.jpg',data).group(0))
                member.img_url = res_url
                member.save()
            except:
                logger.debug('couldn\'t update img_url for member %d' %
                             member.id)
