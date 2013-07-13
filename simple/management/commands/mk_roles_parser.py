#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
import urllib
from BeautifulSoup import BeautifulSoup
import logging
logger = logging.getLogger("open-knesset.mk_roles_parser")

GOVT_INFO_PAGE = r"http://www.knesset.gov.il/mk/heb/MKIndex_Current.asp?view=4";

possible_role_prefix = [ 'שר'.decode('utf8'),
                         'סגן'.decode('utf8'),
                         'סגנית'.decode('utf8'),
                         'שרת'.decode('utf8'),
                         'ראש'.decode('utf8'),
                         'שרה'.decode('utf8')]

def parse_mk_govt_roles():
    info_dict = {}
    soup = BeautifulSoup(urllib.urlopen(GOVT_INFO_PAGE).read().decode('windows-1255').encode('utf-8'))
    tags = soup.findAll(lambda tag: tag.name == 'div' and tag.has_key('class') and ((tag['class']=='MKIconM') or (tag['class']=='MKIconF')))
    for tag in tags:
        mk_id = tag.first().get('href').split('=')[1]
        mk_roles_string = tag.find('span').contents[0]
        mk_roles = mk_roles_string.split(',')
        for i in range(0, len(mk_roles)):
            if i >= len(mk_roles):
                break;
            role = mk_roles[i].strip()
            if not any(role.partition(' ')[0] in s for s in possible_role_prefix):
                mk_roles[i-1] = mk_roles[i-1] + ', ' + mk_roles[i]
                del mk_roles[i]
        info_dict[mk_id] = '|'.join(mk_roles)
    return info_dict

KNESSET_INFO_PAGE = r"http://www.knesset.gov.il/mk/heb/MKIndex_Current.asp?view=7";
V1 = 'ועדת '.decode('utf8')
V2 = 'ועדה '.decode('utf8')
PREFIX = 'יו"ר '.decode('utf8')
def parse_mk_knesset_roles():
    info_dict = {}
    soup = BeautifulSoup(urllib.urlopen(KNESSET_INFO_PAGE).read().decode('windows-1255').encode('utf-8'))
    tags = soup.findAll(lambda tag:tag.name=='tr' and tag.first().has_key('class') and ((tag.first()['class']=='MKIconM') or (tag.first()['class']=='MKIconF')))
    for tag in tags:
        try:
            t = tag.find('a',{'style':"color:Black;"}).contents[0]
        except UnicodeEncodeError:
            logger.warn('error parsing roles tag: %s' % tag.find('a',{'style':"color:Black;"}).contents[0])
            continue
        if (t.find(V1)>=0) or (t.find(V2)>=0):    
            mk_id = tag.find('a').get('href').split('=')[1]
            mk_roles = PREFIX + tag.find('a',{'style':"color:Black;"}).contents[0]
            info_dict[mk_id] = mk_roles
    return info_dict

