import logging

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from mks.models import Member
from committees.models import Committee
from fuzzy_match import fuzzy_match

logger = logging.getLogger("open-knesset.mmm.models")

def text_lookup(Model, text):
    """receives a text and a Model and returns a list of Model objects found in the text"""

    result = []

    for m in Model.objects.all():
        if m.name in text:
            result.append(m.id)
        else:
            if fuzzy_match(m.name, text):
                logger.warning('No exact match found. Performing fuzzy matching!')
                result.append(m.id)

    return result

#from json helper function
def verify(o, d, mks, committees):
    if not hasattr(d, 'title'):
        logger.warning(d)
    if all([d.title == o['title'] ,d.publication_date == o['date'] , d.author_names == o['author']]):
        if (mks and mks == list(d.req_mks.values_list('pk', flat=True))) or (committees and committees == list(d.req_committee.values_list('pk', flat=True))):
            logger.info("%s already exists in db" % o['url'])
            return False
        else:
            logger.info("Found differences between imported data and our db. Performing Update!")
            return True
    else:
        logger.warning("Failed DB verification! Encountered multiple conflicts between the object in our db and imported data.")
        return False


class DocumentManager(models.Manager):

    def from_json(self, j):
      # checking if the db already has document o instance and if no, creating one
        for o in j:
            mks = text_lookup(Member, o['heading'])
            committees = text_lookup(Committee, o['heading'])

            try:
                d = self.get(url=o['url'])
            except ObjectDoesNotExist:
                logger.info("Creating new Document instance: %s" % o['url'])
                d = self.create(url=o['url'], title=o['title'], publication_date=o['date'], author_names=o['author'])
                d.req_committee = committees
                d.req_mks = mks

            if verify(o, d, mks, committees):
               d.req_mks = mks
               d.req_committee = committees

class Document(models.Model):
    url = models.URLField(unique=True)
    title = models.CharField(max_length=2000)
    publication_date = models.DateField(blank=True, null=True, db_index=True)
    # requesting committee
    req_committee = models.ManyToManyField(Committee,
                                            related_name='mmm_documents',
                                            blank=True, null=True)
    # requesting members
    req_mks = models.ManyToManyField(Member,
                                     related_name='mmm_documents',
                                     blank=True, null=True)
    author_names = models.CharField(max_length=500, blank=True)

    objects = DocumentManager()


    def __unicode__(self):
        return self.title


