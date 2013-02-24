# encoding: utf-8

import re,logging
from xml.etree import ElementTree
import committees.models

logger = logging.getLogger("open-knesset.plenum.create_protocol_parts")

def _plenum_parseParaElement(para):
    isBold=False
    if para.find('emphasis') is not None:
        isBold=True
    txt=''
    for subtext in para.itertext():
        txt+=subtext
    return (isBold,txt)

def _plenum_parseParaText(para,isBold):
    t='text'
    if isBold and re.search(r":[\s]*$",para) is not None:
        # bold + ends with a colon
        t='speaker'
    elif isBold:
        t='title'
    return t

def _plenum_parsePara(txt,t,titles):
    if titles is None:
        titles=[]
        if t=='speaker':
            titles.append({u't':u'',u'c':[
                {u't':txt,u'c':[],u's':1}
            ]})
        elif t=='title':
            titles.append({u't':txt,u'c':[]})
        else:
            titles.append({u't':'',u'c':[
                {u't':txt,u's':0}
            ]})
    elif t=='title':
        titles.append({u't':txt,u'c':[]})
    else:
        title=titles[len(titles)-1]
        children=title['c']
        if t=='speaker':
            children.append({u't':txt,u'c':[],u's':1})
        elif len(children)==0:
            children.append({u't':txt,u's':0})
        elif children[len(children)-1]['s']==1:
            children[len(children)-1]['c'].append({u't':txt})
        else:
            children.append({u't':txt,u's':0})
    return titles

_parts=None

def _savePart(meeting,header,body,type):
    global _partsCounter
    global _parts
    _parts.append(
        committees.models.ProtocolPart(meeting=meeting, order=len(_parts), header=header.strip(), body=body.strip(), type=type)
    )

def create_plenum_protocol_parts(meeting):
    global _parts
    _parts=[]
    txt=meeting.protocol_text.encode('utf-8')
    tree=ElementTree.fromstring(txt)
    titles=None
    for para in tree.iter('para'):
        (isBold,txt)=_plenum_parseParaElement(para)
        t=_plenum_parseParaText(txt,isBold)
        titles=_plenum_parsePara(txt,t,titles)
    for title in titles:
        titleHeader=title['t'].strip()
        titleBody=[]
        #_savePart(meeting,'',t,'title')
        for child in title['c']:
            if child['s']==1:
                # it's a speaker, save the aggregated title texts
                if len(titleHeader)>0 or len(titleBody)>0:
                    _savePart(meeting,titleHeader,'\n\n'.join(titleBody),'title')
                    titleHeader=''
                    titleBody=[]
                speakerHeader=child['t'].strip()
                speakerText=[]
                for schild in child['c']:
                    t=schild['t'].strip()
                    if len(t)>0:
                        speakerText.append(t)
                _savePart(meeting,speakerHeader,'\n\n'.join(speakerText),'speaker')
            else:
                t=child['t'].strip()
                if len(t)>0:
                    titleBody.append(t)
        if len(titleHeader)>0 or len(titleBody)>0:
            _savePart(meeting,titleHeader,'\n\n'.join(titleBody),'title')
    if len(_parts)>0:
        # find duplicates
        gotDuplicate=False
        otherMeetings=committees.models.CommitteeMeeting.objects.filter(date_string=meeting.date_string).exclude(id=meeting.id)
        if len(otherMeetings)>0:
            for otherMeeting in otherMeetings:
                if otherMeeting.parts.count()==len(_parts):
                    meeting.delete()
                    gotDuplicate=True
        if gotDuplicate:
            logger.debug('got a duplicate meeting - deleting my meeting')
        else:
            committees.models.ProtocolPart.objects.bulk_create(_parts)
            logger.debug('wrote '+str(len(_parts))+' protocol parts')

