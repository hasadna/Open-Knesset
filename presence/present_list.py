import urllib
import codecs
import re
from datetime import datetime
from BeautifulSoup import BeautifulSoup  # for HTML parsing

#############
#   CONSTS  #
#############

# URL
# hebrew r"http://www.knesset.gov.il/presence/heb/PresentList.aspx"
PRESENT_KNESET_URL = r"http://www.knesset.gov.il/presence/eng/PresentList_eng.aspx"

# REGEX
LAST_UPDATE_TIME_ID = "TimeStamp_eng2_lbLastUpdated"  # "Timestamp2_lbLastUpdated" - for the hebrew page
LAST_UPDATE_TIME_REGEX = re.compile('(\d+\/\d+\/\d+\s+\d+:\d+)')
LAST_UPDATE_DATETIME_FORMAT = "%d/%m/%Y %H:%M"
ID_LINK_REGEX = re.compile(r'id_.*=(\d+)')
MK_IMG_ID = re.compile('^dl.*_img')


class KnessetPresenceParser(object):
    '''This class is responsible for pasrsing the Kneset presence HTML page and extract from it all, the Kneset memebrs that are
        in the kneset according to the last presence update.
    '''
    # The time when the parser start to parse
    __check_time = None
    # The last update time when the kneset present page was updated
    __last_update_time = None

    # beutiful soup parsing of the page
    __soup = None

    # Consts
    __MK_NOT_PRESENT_IMG_CLASS_STR = 'PhotoAsistno'
    __MK_PRESENT_IMG_CLASS_STR = 'PhotoAsist'

    def __init__(self):
        '''Class constructor build a presence date by parsing the knesset presence html page'''
        self.__soup = self._get_presence_html_page()
        self.__last_update_time = self._get_lastupdate_time()

    def _is_mk_present(self, tag):
        '''This function gets a image html and states if the MK is present or not according to img class value:
        if the MK is present the class value equals 'PhotoAsist'' otherwise it equals 'PhotoAsistno' '''

        if tag is None or tag.attrMap is None:
            return False

        if 'class' in tag.attrMap and tag['class'] == self.__MK_PRESENT_IMG_CLASS_STR:
            return True
        return False

    def _is_mk_not_present(self, tag):
        '''This function gets a image html and states if the MK is present or not according to img class value:
        if the MK is present the class value equals 'PhotoAsist'' otherwise it equals 'PhotoAsistno' '''

        if tag is None or tag.attrMap is None:
            return False

        if 'class' in tag.attrMap and tag['class'] == self.__MK_NOT_PRESENT_IMG_CLASS_STR:
            return True
        return False

    def _get_mk_href_tag(self, img_tags_list):
        ''' The function gets img tag list with mk picture in it and return the MK link TAG list
        '''

        a_tag_list = []
        # we got all the images that are not in gray so now we need to find the id of the member we do that
        # by finding the img 'td' parent and extracting the id value from it
        for img_tag in img_tags_list:
            td_tag = img_tag.findParent()

            # sanity check
            if (td_tag.name.lower() != 'td'):
                raise Exception("Img MK parent expected to by 'td' tag got %s tag instead" % td_tag.name)

            a_tag_list.append(td_tag.find('a'))

        return a_tag_list

    def _get_id_from_link(self, link):
        '''Gets the MK id from the url link '''
        return ID_LINK_REGEX.findall(link)[0]

    def _get_mks_ids_by_func(self, select_func=lambda x: True):
        '''Get all the imgs soup tag the returns True when the selection function checks them'''
        imgs_list = self.__soup.findAll(id=MK_IMG_ID)
        present_mk_limg_tag_list = [img for img in imgs_list if select_func(img)]

        a_tag_list = self._get_mk_href_tag(present_mk_limg_tag_list)
        return [int(self._get_id_from_link(a['href'])) for a in a_tag_list]

    def get_present_mks_ids(self):
        '''Return all the ids of the MKs that present in the knesset according to the Knesset website'''
        return self._get_mks_ids_by_func(self._is_mk_present)

    def get_not_present_mks_ids(self):
        '''Return all the ids of teh MKs that are not present in the kneset according to the Kneset website'''
        return self._get_mks_ids_by_func(self._is_mk_not_present)

    def _get_presence_html_page(self):
        '''Return the presence HTML page'''
        html_page = urllib.urlopen(PRESENT_KNESET_URL).read()
        return BeautifulSoup(html_page)

    def _get_lastupdate_time(self):
        '''Returns the last update date of the presence page'''
        d = str(self.__soup.find(id=LAST_UPDATE_TIME_ID))
        update_date_result = LAST_UPDATE_TIME_REGEX.findall(d)
        if len(update_date_result) != 1:
            raise Exception("Error: Parsing  kneset present page could not find last update time")

        return datetime.strptime(update_date_result[0], LAST_UPDATE_DATETIME_FORMAT)

    @property
    def lastupdate_date(self):
        return self.__last_update_time


def test():
    k = KnessetPresenceParser()
    print "last update time is %s" % str(k.lastupdate_date)
    print "The following MKS were present"
    l = k.get_present_mks_ids()
    print l
    print "Total %s MKs present\n" % len(l)
    print "-" * 30
    print "The following MKS were not present\n"
    l = k.get_not_present_mks_ids()
    print l
    print "Total %s MKs not present" % len(l)


#############
#   Main    #
#############
if __name__ == '__main__':
    test()
