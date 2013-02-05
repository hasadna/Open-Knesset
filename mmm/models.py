import logging

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from mks.models import Member
from committees.models import Committee

from django.db import transaction


logger = logging.getLogger("open-knesset.mmm.models")

# FREEZE_ATTR_NAME="frozen"

# entity type tags
MK_TYPE = "MK"
COMM_TYPE = "COMM"

SUPPORTED_SCHEMA_VER = 2

class DocumentManager(models.Manager):

    @transaction.commit_manually
    def from_json(self,  json):
        from itertools import chain

        assert json['meta']['schema_version'][0] == SUPPORTED_SCHEMA_VER # current version

        assert ("matches" in json['objects'] and
                   "documents" in json['objects'])

        # Should probably stick this somewhere on the about page
        # as long as update is not nightly. for now - do nothing with it.
        retrieval_date = json['meta']['retrieval_date']

        #########################################################################
        # coalesce multiple entity matches by document url into single dict entry
        docs=dict()
        for m in chain( json['objects']['matches'], json['objects']['documents']):
            if m.get('entity_id') and  int(m.get('entity_id')) <= 0:
                continue

            default = dict(url=m['url'],
                                  title=m['title'],
                                  publication_date=m['pub_date'],
                                  author_names=m['authors'],
                                  req_mks = [],
                                  req_committee = [])

            doc = docs.get(m['url'],default)

            entity_id =  int(m.get('entity_id',0))
            if m.get('entity_type') == MK_TYPE:
                doc['req_mks'] = list(set(doc['req_mks']+[entity_id]))
            elif m.get('entity_type') == COMM_TYPE :
                doc['req_committee'] =   list(set(doc['req_committee']+ [entity_id]))
            elif m.get('entity_type'):
                logger.warning("Unrecognized match type: {0}".format(m['entity_type']))

            docs[m['url']] = doc


        ################################################################
        # push all documents to db, update linked entities if they exist
        logger.info("Pushing mmm documents to db")
        cnt=0;
        new_cnt=0;
        for d in docs.values():
            cnt+=1
            # m2m fields, pop and save aside, can't call Document()
            # with m2m fields directly
            req_mks = d.pop("req_mks",[])
            req_committee = d.pop("req_committee",[])

            try:
                o = self.get(url=d['url'])

            except ObjectDoesNotExist:
                new_cnt +=1
                o =  Document(**d)
                o.save()

            # populate entry entirely with fixture data, clobbers old values
            for k in d.keys():
                setattr(o,k,d[k])

            o.req_mks = req_mks
            o.req_committee =  req_committee
            o.save()

            if cnt % 500 == 0:
                transaction.commit()
                logger.debug("Processed {0} documents so far".format(cnt))

        transaction.commit()
        logger.info("Added a total of {0} new documents".format(new_cnt))


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


