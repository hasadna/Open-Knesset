#encoding: utf-8
import urllib, re
from HTMLParser import HTMLParser
from BeautifulSoup import BeautifulSoup  #for HTML parsing

#############
#   CONSTS  #
#############

#URLS
MK_HTML_INFO_PAGE = r"http://www.knesset.gov.il/mk/heb/mk_print.asp?mk_individual_id_t=";
KNESET_URL = r"http://www.knesset.gov.il"

#REGEXPS
PRESONAL_INFO_KEY_DATA_TAG = re.compile("Data(\s|$)")
PRESONAL_INFO_VALUE_DATA_TAG = re.compile("DataText2?(\s|$)")
INFO_HEADER_TITLE = re.compile("Title2(\s|$)")
MK_IMG_URL = r"/mk/images/members/"

def unescape(s):
    return HTMLParser().unescape(s)

class MKHtmlParser(object):
    __mk_id = None
    __mk_info_dict = {}
    __soup = None

    def __init__(self, mk_id):
        self.__mk_id = mk_id
        self.__mk_info_dict = {}
        self.__soup = self._parse_mk_info_page()
        self.__mk_info_dict['name'] = self._get_mk_name()
        self.__mk_info_dict['img_link'] = self._get_mk_image_link()
        self._parse_mk_info_data()


    def _get_tables_headers(self):
        headers = self.__soup.findAll(lambda tag: tag.name == 'span' and tag.has_key('class') and tag['class'] == INFO_HEADER_TITLE)
        return [unescape(h.string.strip()) for h in headers]

    def _get_mk_name(self):
        '''Extracts the MK name from the HTML page'''
        try:
            name_tag = self.__soup.findAll(lambda tag: tag.name == 'td' and tag.has_key('class') and tag['class'] == 'Name')[0]
            name_tag = name_tag.string.strip()

            return unescape(name_tag)

        except Exception, e:
            print "Error: could not find the name of MK with id=%d -- %s" % (self.__mk_id, str(e))
            return None

    def  _get_mk_image_link(self):
        try:
            img_tag = self.__soup.findAll(lambda tag: tag.name == 'img' and tag.has_key('src') and MK_IMG_URL in tag['src'])[0]
            img_url = KNESET_URL + img_tag['src']
            return img_url


        except Exception, e:
            print "Error: could not find the img of MK with id=%d -- %s" % (self.__mk_id, str(e))
            return None


    def _parse_mk_info_page(self):
        '''Return the presence HTML page'''
        url = MK_HTML_INFO_PAGE + str(self.__mk_id)
        html_page = urllib.urlopen(url).read().decode('windows-1255').encode('utf-8')
        return BeautifulSoup(html_page)

    def _parse_mk_info_data(self):
        '''The function parses the mk information and returns dict with all the extracted info'''
        trs = self.__soup.findAll('tr')

        self.__mk_info_dict.update(self._extract_mk_personal_info(trs))


    def __is_presonal_info_tag(self, tag):
        '''Intrernal function to check if specific tr tag cotanis personal info'''
        if tag is None or tag.name.lower() != 'td':
            return False
        if not tag.has_key('class'):
            return False

        if (not PRESONAL_INFO_KEY_DATA_TAG.match(tag['class'])) and (not PRESONAL_INFO_VALUE_DATA_TAG.match(tag['class'])):
            return False
        return True


    def _extract_mk_personal_info(self, tr_list):
        info_dict = {}
        info_dict.update(self._get_general_personal(tr_list))

        return info_dict

    def _get_general_personal(self, tr_list):
        '''Extract the presonal info from the html'''
        info_dict = {}
        for tr in tr_list:
            tds = tr.findAll(lambda tag: self.__is_presonal_info_tag(tag))
            k, v = (None, None)
            for td in tds:
                    if PRESONAL_INFO_KEY_DATA_TAG.match(td['class']):
                        k = td.string
                        if (k is None or k == '') and len(td.findAll('a')) > 0 :
                            k = td.findAll('a')[0].string
                    if PRESONAL_INFO_VALUE_DATA_TAG.match(td['class']):
                        v = td.string
                        if (v is None or v == '') and len(td.findAll('a')) > 0 :
                            #link data lets get the link value
                            a_href = td.findAll('a')[0]
                            if a_href.has_key('href'):
                                v = a_href['href']

            if k is not None and v is not None:
                k = unescape(k.strip().replace(':', ''))
                v = unescape(v.strip())
                info_dict[k] = v
        return info_dict

    def save_to_file(self, filename):
        f = file(u"%s" % filename, 'wb')
        print self.__mk_info_dict
        for k, v in self.__mk_info_dict.iteritems():
            if k != '':
                f.write("%s\t%s\n" % (repr(k), repr(v)))

        f.close()

    #Properties
    @property
    def Name(self):
        return self.__mk_info_dict['name']

    @property
    def Id(self):
        return self.__mk_id

    @property
    def Dict(self):
        return self.__mk_info_dict


def test():
    m = MKHtmlParser(200)

    print "Name=%s MK-ID=%d" % (m.Name, m.Id)
    print "Details:"
    for k, v in m.Dict.iteritems():
        print "%s = %s" % (k, v)

#############
#   Main    #
#############
if __name__ == '__main__':
    test()
