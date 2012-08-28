from django.core.management.base import NoArgsCommand, CommandError
from knesset.mmm.models import Document
from knesset.settings import DATA_ROOT
import simplejson


class Command(NoArgsCommand):
    help = "Updating mmm table"
    
    def handle_noargs(self, **options):
        
        json = open(DATA_ROOT + 'mmm_matches.json')
        
        Document.objects.from_json(json)