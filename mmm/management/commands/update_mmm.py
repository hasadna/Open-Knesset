import os
from datetime import datetime

from django.core.management.base import NoArgsCommand, CommandError
from django.utils import simplejson

from mmm.models import Document
from knesset.settings import DATA_ROOT

class Command(NoArgsCommand):
    help = "Updating mmm table"


    def handle_noargs(self, **options):
        FIXTURE_FILE = "mmm.json"

        try:
            f =  open(DATA_ROOT + FIXTURE_FILE, 'rt')
            j = simplejson.load(f)
            for m in j['objects']['matches']:
                # we're promised iso8601
                m['pub_date'] = datetime.strptime(m['pub_date'], '%Y-%m-%d').date()

            Document.objects.from_json(j)

        finally:
            f.close();
