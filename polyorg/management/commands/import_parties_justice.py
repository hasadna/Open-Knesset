# encoding: utf-8
from BeautifulSoup import BeautifulSoup
import urllib2

from django.core.management.base import BaseCommand
from polyorg.models import Party
from HTMLParser import HTMLParser

TABLE_ADDRESS = 'http://www.justice.gov.il/MOJHeb/RasutHataagidim/RashamMiflagot/ChapesMeyda/reShimatMiflagot.htm'


class Command(BaseCommand):
    help = '''Import the list of polyorg parties 
        from the justice ministry website'''
    
    def handle(self, *args, **kwargs):
        self.stdout.write('contacting justice ministry website')
        page = urllib2.urlopen(TABLE_ADDRESS)
        soup = BeautifulSoup(page.read())
        tbl = soup.find('table', 'MsoNormalTable')
        parser = HTMLParser()
        for row in tbl.findAll('tr'):
            text = row.find('td').p.span.string
            if text:
                Party.objects.get_or_create(
                    name=parser.unescape(row.find('td').p.span.string))
