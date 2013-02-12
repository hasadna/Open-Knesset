#encoding: utf-8
import urllib,urllib2
from urlparse import urlparse
import datetime
import re
import logging
import os

from BeautifulSoup import BeautifulSoup
from HTMLParser import HTMLParseError

from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType

from links.models import Link, LinkedFile
import parse_knesset_bill_pdf
from parse_government_bill_pdf import GovProposalParser
from laws.models import (Bill, Law, GovProposal)

logger = logging.getLogger("open-knesset.parse_laws")

# don't parse laws from an older knesset
CUTOFF_DATE = datetime.date(2009,02,24)

class ParseLaws(object):
    """partially abstract class for parsing laws. contains one function used in few
       cases (private and other laws). this function gives the required page
    """

    url = None

    def get_page_with_param(self,params):
        logger.debug('get_page_with_param: self.url=%s, params=%s' % (self.url, params))
        if params == None:
            try:
                html_page = urllib2.urlopen(self.url).read().decode('windows-1255').encode('utf-8')
            except urllib2.URLError:
                logger.error("can't open URL: %s" % self.url)
                return None
            try:
                soup = BeautifulSoup(html_page)
            except HTMLParseError, e:
                logger.debug("parsing URL: %s - %s. will try harder." % (self.url, e))
                html_page = re.sub("(?s)<!--.*?-->"," ", html_page) # cut anything that looks suspicious
                html_page = re.sub("(?s)<script>.*?</script>"," ", html_page)
                html_page = re.sub("(?s)<!.*?>"," ", html_page)
                try:
                    soup = BeautifulSoup(html_page)
                except HTMLParseError, e:
                    logger.debug("error parsing URL: %s - %s" % (self.url, e))
                    return None
            return soup
        else:
            data = urllib.urlencode(params)
            try:
                url_data = urllib2.urlopen(self.url,data)
            except urllib2.URLError:
                logger.error("can't open URL: %s" % self.url)
                return None
            html_page = url_data.read().decode('windows-1255').encode('utf-8')
            try:
                soup = BeautifulSoup(html_page)
            except HTMLParseError, e:
                logger.debug("error parsing URL: %s - %s" % (self.url, e))
                return None
            return soup

def fix_dash(s):
    """returns s with normalized spaces before and after the dash"""
    if not s:
        return None
    m = re.match(r'(תיקון)( ?)(-)( ?)(.*)'.decode('utf8'),s)
    if not m:
        return s
    return ' '.join(m.groups()[0:5:2])

class ParsePrivateLaws(ParseLaws):
    """a class that parses private laws proposed
    """

    #the constructor parses the laws data from the required pages
    def __init__(self,days_back):
        self.url =r"http://www.knesset.gov.il/privatelaw/Plaw_display.asp?lawtp=1"
        self.rtf_url=r"http://www.knesset.gov.il/privatelaw"
        self.laws_data=[]
        self.parse_pages_days_back(days_back)

    #parses the required pages data
    def parse_pages_days_back(self,days_back):
        today = datetime.date.today()
        last_required_date = today + datetime.timedelta(days=-days_back)
        last_law_checked_date = today
        index = None
        while last_law_checked_date > last_required_date:
            if index:
                params = {'RowStart':index}
            else:
                params = None
            soup_current_page = self.get_page_with_param(params)
            if not soup_current_page:
                return
            index = self.get_param(soup_current_page)
            self.parse_private_laws_page(soup_current_page)
            last_law_checked_date = self.update_last_date()

    def get_param(self,soup):
        name_tag = soup.findAll(lambda tag: tag.name == 'a' and tag.has_key('href') and re.match("javascript:SndSelf\((\d+)\);",tag['href']))
        m=re.match("javascript:SndSelf\((\d+)\);",name_tag[0]['href'])
        return m.groups(1)[0]

    def parse_private_laws_page(self,soup):
        name_tag = soup.findAll(lambda tag: tag.name == 'tr' and tag.has_key('valign') and tag['valign']=='Top')
        for tag in name_tag:
            tds = tag.findAll(lambda td: td.name == 'td')
            x={}
            x['knesset_id'] = int(tds[0].string.strip())
            x['law_id'] = int(tds[1].string.strip())
            if tds[2].findAll('a')[0].has_key('href'):
                x['text_link'] = self.rtf_url + r"/" + tds[2].findAll('a')[0]['href']
            x['law_full_title'] = tds[3].string.strip()
            m = re.match(u'הצעת ([^\(,]*)(.*?\((.*?)\))?(.*?\((.*?)\))?(.*?,(.*))?',x['law_full_title'])
            if not m:
                logger.warn("can't parse proposal title: %s" % x['law_full_title'])
                continue
            x['law_name'] = m.group(1).strip().replace('\n','').replace('&nbsp;',' ')
            comment1 = m.group(3)
            comment2 = m.group(5)
            if comment2:
                x['correction'] = comment2.strip().replace('\n','').replace('&nbsp;',' ')
                x['comment'] = comment1
            else:
                x['comment'] = None
                if comment1:
                    x['correction'] = comment1.strip().replace('\n','').replace('&nbsp;',' ')
                else:
                    x['correction'] = None
            x['correction'] = fix_dash(x['correction'])
            x['law_year'] = m.group(7)
            x['proposal_date'] = datetime.datetime.strptime(tds[4].string.strip(), '%d/%m/%Y').date()
            names_string = ''.join([unicode(y) for y in tds[5].findAll('font')[0].contents])
            names_string = names_string.replace('\n','').replace('&nbsp;',' ')
            proposers = []
            joiners = []
            if re.search('ONMOUSEOUT',names_string)>0:
                splitted_names= names_string.split('ONMOUSEOUT')
                joiners = [ name for name in re.match('(.*?)\',\'',splitted_names[0]).group(1).split('<br />') if len(name)>0 ]
                proposers = splitted_names[1][10:].split('<br />')
            else:
                proposers = names_string.split('<br />')
            x['proposers'] = proposers
            x['joiners'] = joiners
            self.laws_data.append(x)

    def update_last_date(self):
        return self.laws_data[-1]['proposal_date']

class ParseKnessetLaws(ParseLaws):
    """A class that parses Knesset Laws (laws after committees)
	   the constructor parses the laws data from the required pages
    """
    def __init__(self,min_booklet):
        self.url =r"http://www.knesset.gov.il/laws/heb/template.asp?Type=3"
        self.pdf_url=r"http://www.knesset.gov.il"
        self.laws_data=[]
        self.min_booklet = min_booklet
        self.parse_pages_booklet()

    def parse_pages_booklet(self):
        full_page_parsed = True
        index = None
        while full_page_parsed:
            if index:
                params = {'First':index[0],'Start':index[1]}
            else:
                params = None
            soup_current_page = self.get_page_with_param(params)
            index = self.get_param(soup_current_page)
            full_page_parsed = self.parse_laws_page(soup_current_page)

    def get_param(self,soup):
        name_tag = soup.findAll(lambda tag: tag.name == 'a' and tag.has_key('href') and re.match("javascript:SndSelf\((\d+),(\d+)\);",tag['href']))
        if name_tag:
            m = re.match("javascript:SndSelf\((\d+),(\d+)\);",name_tag[0]['href'])
            return m.groups()
        else:
            return None

    def parse_pdf(self,pdf_url):
        return parse_knesset_bill_pdf.parse(pdf_url)

    def parse_laws_page(self,soup):
        name_tag = soup.findAll(lambda tag: tag.name == 'a' and tag.has_key('href') and tag['href'].find(".pdf")>=0)
        for tag in name_tag:
            pdf_link = self.pdf_url + tag['href']
            booklet = re.search(r"/(\d+)/",tag['href']).groups(1)[0]
            if int(booklet) <= self.min_booklet:
                return False
            pdf_data = self.parse_pdf(pdf_link) or []
            for j in range(len(pdf_data)): # sometime there is more than 1 law in a pdf
                title = pdf_data[j]['title']
                m = re.findall('[^\(\)]*\((.*?)\)[^\(\)]',title)
                try:
                    comment = m[-1].strip().replace('\n','').replace('&nbsp;',' ')
                    law = title[:title.find(comment)-1]
                except:
                    comment = None
                    law = title.replace(',','')
                try:
                    correction = m[-2].strip().replace('\n','').replace('&nbsp;',' ')
                    law = title[:title.find(correction)-1]
                except:
                    correction = None
                correction = fix_dash(correction)
                law = law.strip().replace('\n','').replace('&nbsp;',' ')
                if law.find("הצעת ".decode("utf8"))==0:
                    law = law[5:]

                law_data = {'booklet':booklet,'link':pdf_link, 'law':law, 'correction':correction,
                                       'comment':comment, 'date':pdf_data[j]['date']}
                if 'original_ids' in pdf_data[j]:
                    law_data['original_ids'] = pdf_data[j]['original_ids']
                if 'bill' in pdf_data[j]:
                    law_data['bill'] = pdf_data[j]['bill']
                self.laws_data.append(law_data)
        return True

    def update_booklet(self):
        return int(self.laws_data[-1]['booklet'])

class ParseGovLaws(ParseKnessetLaws):

    def __init__(self,min_booklet):
        self.url =r"http://www.knesset.gov.il/laws/heb/template.asp?Type=4"
        self.pdf_url=r"http://www.knesset.gov.il"
        self.laws_data=[]
        self.min_booklet = min_booklet

    def parse_gov_laws(self):
        """ entry point to start parsing """
        self.parse_pages_booklet()

    def parse_pdf(self,pdf_url):
        """ Grab a single pdf url, using cache via LinkedFile
        """
        existing_count = Link.objects.filter(url=pdf_url).count()
        if existing_count >= 1:
            if existing_count > 1:
                print "WARNING: you have two objects with the url %s. Taking the first" % pdf_url
            link = Link.objects.filter(url=pdf_url).iterator().next()
        filename = None
        if existing_count > 0:
            files = [f for f in link.linkedfile_set.order_by('last_updated') if f.link_file.name != '']
            if len(files) > 0:
                link_file = files[0]
                filename = link_file.link_file.path
                logger.debug('reusing %s from %s' % (pdf_url, filename))
        if not filename:
            logger.debug('getting %s' % pdf_url)
            contents = urllib2.urlopen(pdf_url).read()
            link_file = LinkedFile()
            saved_filename = os.path.basename(urlparse(pdf_url).path)
            link_file.link_file.save(saved_filename, ContentFile(contents))
            filename = link_file.link_file.path
        prop = GovProposalParser(filename)

        # TODO: check if parsing handles more than 1 prop in a booklet
        x = [{'title':prop.get_title(),
              'date':prop.get_date(),
              #'bill':prop,
              'link_file': link_file}]
        return x

    def update_single_bill(self, pdf_link, booklet=None, alt_title=None):
        if booklet is None:
            # get booklet from existing bill
            if GovProposal.objects.filter(source_url=pdf_link).count() < 1:
                logger.error('no existing object with given pdf link and no booklet given. pdf_link = %s' % pdf_link)
                return
            booklet = GovProposal.objects.filter(source_url=pdf_link)[0].booklet_number
        pdf_data = self.parse_pdf(pdf_link)
        for j in range(len(pdf_data)): # sometime there is more than 1 law in a pdf
            if alt_title: # just use the given title
                title = alt_title
            else: # get the title from the PDF file itself. doesn't work so well
                title = pdf_data[j]['title']
            m = re.findall('[^\(\)]*\((.*?)\)[^\(\)]',title)
            try:
                comment = m[-1].strip().replace('\n','').replace('&nbsp;',' ')
                law = title[:title.find(comment)-1]
            except:
                comment = None
                law = title.replace(',','')
            try:
                correction = m[-2].strip().replace('\n','').replace('&nbsp;',' ')
                law = title[:title.find(correction)-1]
            except:
                correction = None
            correction = fix_dash(correction)
            law = law.strip().replace('\n','').replace('&nbsp;',' ')
            if law.find("הצעת ".decode("utf8"))==0:
                law = law[5:]

            law_data = {'booklet':booklet,'link':pdf_link, 'law':law, 'correction':correction,
                                   'comment':comment, 'date':pdf_data[j]['date']}
            if 'original_ids' in pdf_data[j]:
                law_data['original_ids'] = pdf_data[j]['original_ids']
            if 'bill' in pdf_data[j]:
                law_data['bill'] = pdf_data[j]['bill']
            self.laws_data.append(law_data)
            self.create_or_update_single_bill(proposal=law_data, pdf_link=pdf_link,
                                              link_file=pdf_data[j]['link_file'])

    def create_or_update_single_bill(self, proposal, pdf_link, link_file):
        if not(proposal['date']) or CUTOFF_DATE and proposal['date'] < CUTOFF_DATE:
            return
        law_name = proposal['law']
        (law, created) = Law.objects.get_or_create(title=law_name)
        if created:
            law.save()
        if law.merged_into:
            law = law.merged_into
        title = u''
        if proposal['correction']:
            title += proposal['correction']
        if proposal['comment']:
            title += ' ' + proposal['comment']
        if len(title)<=1:
            title = u'חוק חדש'
        (gp,created) = GovProposal.objects.get_or_create(booklet_number=proposal['booklet'], knesset_id=18,
                                                             source_url=proposal['link'],
                                                             title=title, law=law, date=proposal['date'])
        if created:
            gp.save()
            logger.debug("created GovProposal id = %d" % gp.id)

        bill_params = dict(law=law, title=title, stage='3', stage_date=proposal['date'])
        similar_bills = Bill.objects.filter(**bill_params).order_by('id')
        if len(similar_bills) >= 1:
            b = similar_bills[0]
            if len(similar_bills) > 1:
                logger.debug("multiple bills detected")
                for bill in similar_bills:
                    if bill.id == b.id:
                        logger.debug("bill being used now   - %d" % bill.id)
                    else:
                        logger.debug("bill with same fields - %d" % bill.id)
        else:
            b = Bill(**bill_params)
            b.save()
        gp.bill = b
        gp.save()
        if link_file.link is None:
            link = Link(title=pdf_link, url=pdf_link,
                content_type=ContentType.objects.get_for_model(gp),
                object_pk=str(gp.id))
            link.save()
            link_file.link = link
            link_file.save()
            logger.debug("check updated %s" % b.get_absolute_url())

    def parse_laws_page(self,soup):
        # Fall back to regex, because these pages are too broken to get the
        # <td> element we need with BS"""
        u = unicode(soup)
        m = re.findall('class="LawText1">(.*?)</',u)
        # get the link to the PDF file
        name_tag = soup.findAll(lambda tag: tag.name == 'a' and tag.has_key('href') and tag['href'].find(".pdf")>=0)
        for title,tag in zip(m,name_tag):
            pdf_link = self.pdf_url + tag['href']
            booklet = re.search(r"/(\d+)/",tag['href']).groups(1)[0]
            if int(booklet) <= self.min_booklet:
                return False
            #title = tag.findNext(attrs={"class":"LawText1"}).findNext(attrs={"class":"LawText1"}).text
            self.update_single_bill(pdf_link, booklet=booklet, alt_title=title)
        return True


#############
#   Main    #
#############

if __name__ == '__main__':
    m = ParsePrivateLaws(15)


