import urllib2
import re

from django.core.management.base import NoArgsCommand,BaseCommand, CommandError
#from django.core.files.base import ContentFile
#from django.contrib.auth.models import User, Group

#from actstream import follow

from mks.models import Member
#from avatar.models import Avatar

class Command(NoArgsCommand):
    help = "update member url_img"

    def handle_noargs(self, **options):
        # TODO: ---
        for member in Member.objects.all():
            mk_id = member.id
	    searchUrl='http://www.knesset.gov.il/mk/heb/ShowPic.asp?mk_individual_id_t=%s'%mk_id
	    resUrl='mk/images/members/'
	    page=urllib2.urlopen(searchUrl)
	    data=page.read()
	    resUrl='http://www.knesset.gov.il/'+re.search('mk/images/members/.*.jpg',data).group(0)
	    member.url_img=resUrl
	    member.save()

	

