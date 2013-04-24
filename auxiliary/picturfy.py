"""  Picturfy turn web pages to PNG images
The main daemon that runs it all

Created on Dec 29, 2012

@author: Guy Sheffer <guysoft at gmail dot com>
"""

import os
import tempfile
## {{{ http://code.activestate.com/recipes/496837/ (r1)
import re

rxcountpages = re.compile(r"$\s*/Type\s*/Page[/\s]", re.MULTILINE|re.DOTALL)
def countPages(filename):
    ''' Count the number of pages in a PDF file, pure python
    
    :param filename: the path to the PDF file
    :return: An int of the number of pages
    '''
    data = file(filename,"rb").read()
    return len(rxcountpages.findall(data))

#print "Number of pages in PDF File:", countPages("test.pdf")
## end of http://code.activestate.com/recipes/496837/ }}}

DEFAULT_HEIGHT=10 #Starting step for estimation of page length ( takes O(|log(height/DEFAULT_HEIGHT)| + 1 )))
DPI="125"
def html2png(url,width,png,verbose=False):
    ''' This is the function that would take web pages and turn them to PNG images
    It renders first a PDF from webkit
    
    :param url: A string with the URL
    :param width: the width of the page to be rendered (the width of the browser windows in pixels)
    :param png: The path to save the PNG image
    '''
    tmpFile=tempfile.mktemp(suffix=".pdf")
    OUTPUT_FILE=png
    
    height=DEFAULT_HEIGHT/2
    pageCount=2
    args=""
    if not verbose:
        args+=" -q "
    while pageCount != 1:
        height=height*pageCount
        os.system('xvfb-run -a -s "-screen 1 640x480x16" wkhtmltopdf ' + args + ' --dpi ' + DPI + ' -L 0 -R 0 -T 0 -B 0 --page-height ' + str(height)  + 'px --page-width ' + width + "px " + url + " " + tmpFile + " ")
        pageCount=countPages(tmpFile)
        
    os.system('convert -trim +repage -density ' + DPI + ' ' + tmpFile + " " + OUTPUT_FILE)
    os.remove(tmpFile)
    return

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 4:
        print "Usage: " + sys.argv[0] + " <URL> <WIDTH> <PNG>"
        print "eg: "+ sys.argv[0] + " www.google.com 500 google.png"
    url = sys.argv[1]
    width = sys.argv[2]
    png = sys.argv[3]
    print "Downloading and rendering"
    html2png(url,width,png)