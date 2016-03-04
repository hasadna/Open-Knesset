#!/usr/bin/python
# -*- coding: UTF-8 -*-
import cPickle as pickle
from collections import defaultdict

#REMOVE = ['"', "'", '/', '\\', ',', '.', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '=', '_', '+', '\n', '[', ']', '{', '}', '|', '<', '>', '?', '~', ":", ';']
REMOVE = [u'"', u"'", u'/', u'\\', u',', u'.', u'!', u'@', u'#', u'$', u'%', u'^', u'&', u'*', u'(', u')', u'-', u'=', u'_', u'+', u'\n', u'[', u']', u'{', u'}', u'|', u'<', u'>', u'?', u'~', u":", u';', u'–' , u'”', u'`']
REMOVE.extend([unicode(i) for i in xrange(10)])
REMOVE.extend([str(i) for i in xrange(10)])

def make_histogram(t):
    dd = defaultdict(int)
#    for w in t.split():
#        dd[reduce(lambda o, s: o.replace(s, ' '), REMOVE, w)] += 1
    for w in reduce(lambda o, s: o.replace(s, u' '), REMOVE, t).split():
        dd[w] += 1
    return dict(dd)

from collections import defaultdict
ACCEPTED_POS = ['NN', 'JJ', 'VB', 'NNT', 'BN', 'NNP', 'TTL',  ]
def make_pos_histogram(t):
    dd = defaultdict(int)
    for w in [ppp.split('\t')[1] for ppp in t.splitlines() if ppp.count('\t') > 5 and (ppp.split('\t')[3] in ACCEPTED_POS or ppp.split('\t')[4] in ACCEPTED_POS)]:
        dd[w] += 1
    return dict(dd)
    
    
# needed phrases: NN, JJ, VB, NNT, BN
# Use this:
# http://www.cs.bgu.ac.il/~yoavg/depparse/gparse
# or this:
# http://www.cs.bgu.ac.il/~yoavg/constparse/gparse
# or this:
# http://www.cs.bgu.ac.il/~nlpproj/demo/
# from here:
# http://www.cs.bgu.ac.il/~nlpproj/
# seems like:
# http://www.cs.bgu.ac.il/~yoavg/software/hebparsers/hebdepparser/hebdepparser.tgz
# is working good enough

pp_with_tags = pickle.load(open('pp_pos_with_tags.pkl', "rb"))

keywords = set()
data = []
for i, pp in enumerate(pp_with_tags):
    pp_pos, pp_tag, pp_id = pp['pos'], pp['tags'], pp['id']
    
    #print str(i), "/", str(len(pp_with_tags))
    try:
        histogram = make_pos_histogram(pp_pos)
#        histogram = make_histogram(pp_text)
    except:
        import traceback; traceback.print_exc()
        print "at pp", i
        import pdb; pdb.set_trace()
    data.append({'histogram' : histogram, 'tags' : pp_tag, 'id' : pp_id})
    keywords |= set(histogram.keys()) # this will add the keys
    
    

pickle.dump((keywords, data), open('histograms_with_tags.pkl', 'wb'))

