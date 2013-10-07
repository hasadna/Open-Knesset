import os, csv
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.conf import settings
from auxiliary.models import TagSynonym
from tagging.models import Tag
from django.db import IntegrityError

DATA_ROOT = getattr(settings, 'DATA_ROOT',
    os.path.join(settings.PROJECT_ROOT, os.path.pardir, os.path.pardir, 'data'))

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--no-dry-run',
            action='store_true',
            dest='nodryrun',
            default=False,
            help='No Dry Run - default is dry run, set this to run the real process'),
        make_option('--hebrev',
            action='store_true',
            dest='hebrev',
            default=False,
            help='Reverse hebrew strings - to display properly on terminal'),
    )
    
    def _find_tag(self,id,name):
        tags=Tag.objects.filter(id=id)
        if len(tags)==0:
            self.stdout.write('-- warning --')        
            self.stdout.write('could not find tag')
            self.stdout.write('--------------------')
            return None
        else:
            tag=tags[0]
            dbName=tag.name
            csvName=name.strip().decode('utf-8')
            if csvName!=dbName:
                self.stdout.write('-- warning --')
                self.stdout.write('tag name does not match name in db')
                self.stdout.write('tag name from db:')
                self.stdout.write(dbName)
                self.stdout.write('--------------------')
                return None
            else:
                return tag
        
    
    def _delete(self,item):
        tag=self._find_tag(item['id'],item['name'])
        if self._options['nodryrun'] and tag is not None:
            tag.delete()
            self.stdout.write('deleted')
    
    def _synonym(self,item):
        tag=self._find_tag(item['id'],item['name'])
        properTags=Tag.objects.filter(name=item['proper_name'])
        if len(properTags)>0:
            properTag=properTags[0]
        else:
            properTag=None
        if tag is not None:
            if properTag is None:
                # got the synonym tag but not the proper tag
                # create the proper tag - so we can link it to the synonym
                properTag=Tag(name=item['proper_name'])
                properTag.save()
            if properTag is not None and properTag!=tag:
                # got the synonym tag and the proper tag - just create the synonym
                try:
                    ts=TagSynonym(tag=properTag,synonym_tag=tag)
                    if self._options['nodryrun']:
                        ts.save()
                        self.stdout.write('done')
                except IntegrityError as e:
                    if str(e)=='column synonym_tag_id is not unique':
                        self.stdout.write('-- warning --')
                        self.stdout.write('synonym already exists')
                        self.stdout.write('--------------------')
                    else:
                        raise e
    
    def _r(self,str):
        if self._options['hebrev']:
            return str.decode('utf-8')[::-1]
        else:
            return str

    def handle(self, *args, **options):
        self._options=options    
        with open(DATA_ROOT+'/tags.csv') as file:
            reader=csv.DictReader(file)
            first=True
            deletes=[]
            synonyms=[]
            for row in reader:
                # fields in row:
                # 'NUMBER OF ITEMS', 'NAME', 'ID', 'delete', 'mother tag'
                if row['delete'].strip()=='1':
                    motherTag=row['mother tag'].strip()
                    name=row['NAME'].strip()
                    id=row['ID'].strip()
                    if motherTag=='':
                        deletes.append({'id':id,'name':name})
                    else:
                        synonyms.append({'id':id,'name':name,'proper_name':motherTag})
            self.stdout.write("\n\ndelete tags:\n")
            for item in deletes:
                self.stdout.write(item['id']+': "'+self._r(item['name'])+'"')
                self._delete(item)
            self.stdout.write("\n\ncreate synonyms:\n")
            for item in synonyms:
                self.stdout.write(item['id']+': "'+self._r(item['name'])+'" synonym for: "'+self._r(item['proper_name'])+'"')
                self._synonym(item)




