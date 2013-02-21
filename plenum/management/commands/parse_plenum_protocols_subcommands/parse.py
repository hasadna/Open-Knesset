# encoding: utf-8

import datetime,traceback,sys,os,re,subprocess,json,io,logging
import xml.etree.ElementTree as ET
from django.conf import settings
from django.db.models import Count
from committees.models import Committee, CommitteeMeeting

verbosity=1

def Parse(verbosity_level,reparse):
    global verbosity
    verbosity=int(verbosity_level)
    #DATA_ROOT = getattr(settings, 'DATA_ROOT')
    plenum=Committee.objects.filter(type='plenum')[0]
    meetings=CommitteeMeeting.objects.filter(committee=plenum).exclude(protocol_text='')
    if not reparse:
        meetings=meetings.annotate(Count('parts')).filter(parts__count=0)
    if verbosity>1:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(console)
    for meeting in meetings:
        meeting.create_protocol_parts(delete_existing=reparse)
