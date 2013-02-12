# coding=utf-8

from difflib import get_close_matches
from collections import namedtuple
import re
import datetime
#import pyfribidi

from util import flatten
from textutil import reverse_numbers, asblocks, fix_superscripts
from pdftools import pdftotext, pdfinfo

DEBUG = False

def readable(txt):
    if isinstance(txt, list):
        txt = '\n'.join(txt)
    #return '\n'.join([pyfribidi.log2vis(unicode(l)) for l in txt.split('\n')])
    return '\n'.join([unicode(l) for l in txt.split('\n')])

def show_blocks(bs):
    return readable(flatten(zip(bs, ['\n']*len(bs))))
def show_block(bs):
    return readable(bs)

def asreversed_number_blocks(text):
    return asblocks([reverse_numbers(l).strip() for l in text])

def rearrange_header(block, parts):
    """ Rearrange a badly extracted header of a paragraph.

    The explanation text usually start with some text on the right that comes out
    in the second line - 
     XXXXXXXX YYYY
     ZZZZZZZZZZZZZ
    comes out as
     XXXXXXXXX
     YYYY
     ZZZZZZZZZZZ
    which is fine if this was left to right, but we are right to left.. (fix poppler? :)
    This can also become
     XXXXXXXXXXX
     YYY
     Y
     ZZZZZZZZZZZ
    we use common texts to try to identify this.
    """
    if len(block) < 1 + len(parts): return
    for i, p in enumerate(parts):
        if block[i+1] != p:
            return
    block[:len(parts)+1] = ''.join(parts), block[0]

def rearrange_header_in_the_middle(block, parts_list):
    """ Give it a list of headers, each header is a list of strings. It will
    look for the appearance of a header and if found, rearrange to fix
    pdftotext-ism.

    This goes over the block once, complexity len(block)*sum(map(len,parts_list))
    """
    for s in xrange(1, len(block)):
        for parts in parts_list:
            for i, p in enumerate(parts):
                if block[s+i] != p:
                    break
            else:
                # match
                block[s-1:len(parts)+s] = ''.join(parts), block[s-1]
                break

def non_empty(block):
    for l in block:
        if len(l) > 0:
            return True
    return False

def remove_single_char_lines(b):
    for l in b:
        if len(l.strip()) == 0:
            print "removing %s" % l
        else:
            yield l

HC = HebrewConstant = lambda x: unicode(x, 'utf8')

MITPARSEM = HC('מתפרסמת בבזה הצעת חוק מטעם הממשלה:')
HESBER = HC('דברי הסבר')

CLALI = HC('כללי')
CLALI2 = [HC('כלל'), HC('י')]
SEIF_1 = HC('סעיף 1')

def parse_proposal_page(top_text, bottom_text):
    """ From second page onward the text is divided to two by a title in the middle,
    and contains footnotes at the bottom. We return the three parts. The footnotes
    are a little more of a problem - we need to find out what they usually contain
    """
    #top_blocks = asblocks(reverse_numbers(''.join(top_text)).split('\n'))
    top_text, superscripts = fix_superscripts(top_text)
    if len(superscripts) > 0 and DEBUG:
        print "superscripts = %r" % superscripts
    top_blocks = asreversed_number_blocks(top_text)
    # Here is how a proposal second page looks: (actually the rest are pretty much
    # the same)
    #  starts with a :הלשממה םעטמ קוח תעצה הזבב תמסרפתמ
    # that's a separate block, ignore it.
    if len(top_blocks) >= 1 and get_close_matches(top_blocks[0][0], [MITPARSEM]):
        proposal_block_start = 1
    else:
        proposal_block_start = 0
    # Then you have the title again, but it ends up being attached to some text
    # in front.
    # Then there is the ammendment itself.
    # Then the title "
    explanation_block_start = None
    proposal_blocks = []
    explanation_block = []
    for i, b in enumerate(top_blocks):
        if b[0] == HESBER:
            explanation_block_start = i
            break
    if explanation_block_start:
        exp_block = top_blocks[explanation_block_start]
        # skip the title
        del exp_block[0]
        rearrange_header(exp_block, [CLALI])
        rearrange_header(exp_block, CLALI2)
        # The following blocks are unfortunately not broken on paragraph boundaries -
        # pdftotext bunches them together. We can just try to remove the possible
        # number at the end that is the "1" before footnote 1.
        # We can use limited height to avoid this too
        explanation_blocks_1 = top_blocks[explanation_block_start:]
        before_single_line_removal = sum(map(len, explanation_blocks_1))
        explanation_blocks = map(list,map(remove_single_char_lines, explanation_blocks_1))
        after_single_line_removal = sum(map(len, explanation_blocks))
        if before_single_line_removal != after_single_line_removal:
            print "removed %d single lines" % (before_single_line_removal - after_single_line_removal)
        proposal_blocks = top_blocks[proposal_block_start:explanation_block_start]
        # pdftotext doesn't correctly get the blocks - they are single
        # lined blocks in the explanation_block_text
        explanation_block = sum(explanation_blocks, [])
        rearrange_header_in_the_middle(explanation_block, [[SEIF_1]])
    #import pdb; pdb.set_trace()
    return GovPage(n_proposal=proposal_block_start, n_details=explanation_block_start,
        proposal=proposal_blocks, details=explanation_block,
        bottom=asreversed_number_blocks(bottom_text),
        superscripts=superscripts)

GovPage = namedtuple('GovPage', "n_proposal n_details proposal details bottom superscripts".split())

class GovProposalParser(object):
    """ Extract text for presentaiton and search from government law proposals.
    
    HOW:

    The Text Selection in poppler is broken. Maybe just in hebrew, dunno.
    But pdftotext, the utility, is fine.
    The columns are generally parsed as if they are consecutive, so they pose
    no problem. The DIVREY HESBER title is found going through the text. The
    bottom part is currently broken - assumed to be at a fixed place, while
    it is clearly not (it is layouted at the highest possible position).

    The numbers are reversed (because the text is in hebrew and pdftotext
    doesn't use a real bidi algorithm) so we fix that too.
    """

    # rect of everything but the footnotes and footer
    top_rect = (0, 0, 1000, 610)
    bottom_rect = (0, 610, 1000, 300) # TODO - remove or calculate per page

    def __init__(self, filename):
        self.filename = filename
        self.info = pdfinfo(self.filename)
        self.page_num = self.info.pages
        self._title = None
        self._full_pages = {} # unparsed text per key, which is number or number and rect
        self._pages = [] # parsed ordered pages
        self._proposal = ''
        self._details = ''

    def to_unicode(self, show_details):
        proposal, details = self.proposal, self.details
        n_proposals = [page.n_proposal for page in self._pages]
        n_details = [page.n_details for page in self._pages]
        lines = [
            "Proposal:",
            "%s: %s" % (self.filename, readable(self.title)),
            "%s: %s" % (self.filename, (n_proposals, n_details, len(proposal), len(details))),
            "+"*20,
            show_blocks(proposal),
            "="*20,
            show_blocks([page.bottom for page in self._pages])]
        if show_details:
            lines.extend([
                "?"*20,
                show_block(details)])
        lines.append("-"*20)
        return u'\n'.join(lines)

    def __str__(self):
        return self.to_unicode(False)

    __repr__ = __str__

    def get_title(self):
        """
        Extract the title of the Government Law Proposal.

        Example title produced:
        http://www.knesset.gov.il/Laws/Data/BillGoverment/538/538.pdf

        2010.-ע"שתה ,(םיילילפה םיכילהה לועיי) (66 'סמ ןוקית) ילילפה ןידה רדס קוח תעצה
        """
        if self._title is None:
            all_title = reverse_numbers(''.join(asblocks(self.get_page_text(0))[-1]))
            self._title = all_title[:all_title.find('. ')].strip().replace('\n', ' ')
        return self._title

    title = property(get_title)

    def get_page_text(self, n, rect=None):
        """ page is zero based - like poppler API (but unlike pdftotext utility) """
        if rect is None:
            key = n
        else:
            key = (n, rect)
        if key not in self._full_pages:
            if rect is None:
                txt = pdftotext(self.filename,first=n+1,last=n+1)
            else:
                x, y, w, h = rect
                txt = pdftotext(self.filename, first=n+1, last=n+1, x=x, y=y, w=w, h=h)
            self._full_pages[key] = txt
        return self._full_pages[key]

    def get_date(self):
        self._parse_doc()
        for page_nr in xrange(len(self._pages)):
            page_text = '\n'.join([x for x in flatten(self._pages[page_nr]) if isinstance(x,unicode)])
            m = re.search('\d{1,2}\.\d{1,2}\.\d{4}',page_text)
            try:
                return datetime.datetime.strptime(m.group(0),'%d.%m.%Y').date()
            except AttributeError:
                # try backwards:
                m = re.search('\d{4}\.\d{1,2}\.\d{1,2}',page_text)
                try:
                    return datetime.datetime.strptime(m.group(0)[::-1],'%d.%m.%Y').date()
                except AttributeError:
                    pass
                pass
        return None

    def _parse_doc(self):
        if len(self._pages) > 0:
            return
        for page_nr in xrange(1, self.page_num):
            self._pages.append(self._parse_page(page_nr))
        self._details = sum((page.details for page in self._pages), [])
        self._proposal = sum((page.proposal for page in self._pages), [])

    def _parse_page(self, nr):
        return parse_proposal_page(top_text=self.get_page_text(nr, self.top_rect),
            bottom_text=self.get_page_text(nr, self.bottom_rect))

    def get_proposal(self):
        """ return main proposal text. this is the paragraph following the title
        and coming before the explanation (DIVREY HESBER)

        It appears on each page, this function returns the concatenation of all
        of the pages.
        """
        self._parse_doc()
        return self._proposal

    proposal = property(get_proposal)

    def get_details(self):
        """ returns the bulk of the document coming after the title "DIVREY HESBER"

        It appears on each page, this function returns the concatenation of all
        of the pages.
        """
        self._parse_doc()
        return self._details

    details = property(get_details)

    def get_page_as_png(self):
        """ The graphics are rendered correctly since we use poppler to do the
        rendering, but are not searchable. So the idea is to use both, perhaps
        link to these images.
        """
        pass

