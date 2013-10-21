import os, csv
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.conf import settings
from auxiliary.models import TagSynonym
from tagging.models import Tag
from django.db import IntegrityError
from django.core.exceptions import ValidationError

DATA_ROOT = getattr(settings, 'DATA_ROOT',
    os.path.join(settings.PROJECT_ROOT, os.path.pardir, os.path.pardir, 'data'))

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--no-dry-run',
            action='store_true',
            dest='nodryrun',
            default=False,
            help='No Dry Run - default is dry run, set this to run the real process'),
    )
    
    def handle(self, *args, **options):
        self._options=options
        for ts in TagSynonym.objects.all():
            if ts.tag!=ts.synonym_tag and ts.synonym_tag.items.count()>0:
                self.stdout.write('')
                self.stdout.write('copying tagged items from tag:')
                self.stdout.write(str(ts.synonym_tag.id)+': '+ts.synonym_tag.name)
                self.stdout.write('to tag:')
                self.stdout.write(str(ts.tag.id)+': '+ts.tag.name)
                self.stdout.write('objects:')
                for ti in ts.synonym_tag.items.all():
                    self.stdout.write(ti.content_type.name+u': '+unicode(ti.object_id))
                    ti.tag=ts.tag
                    ok=True
                    delti=False
                    try:
                        ti.full_clean()
                    except ValidationError as e:
                        if e.message_dict == {'__all__': [u'Tagged item with this Tag, Content type and Object id already exists.']}:
                            # the same object is tagged to both the synonym tag and the proper tag
                            # delete it from the synonym tag
                            self.stdout.write('object is already tagged on proper tag, delete from synonym')
                            delti=True
                        else:
                            self.stdout.write('validation error:')
                            self.stdout.write(str(e.message_dict))
                            ok=False
                    if ok and options['nodryrun']:
                        try:
                            if delti:
                                ti.delete()
                            else:
                                ti.save()
                            self.stdout.write('done')
                        except IntegrityError as e:
                            self.stdout.write('IntegrityError:')
                            self.stdout.write(str(e))




