#!/usr/bin/python
# -*- coding: UTF-8 -*-
import numpy
import numpy as np
import re
from functools import partial
from sklearn.externals import joblib
import cPickle as pickle
from collections import defaultdict
lb = pickle.load(open("classifier_data/label_binarizer.pkl", "rb"))
keywords, data = pickle.load(open('histograms_with_tags.pkl', 'rb'))
pp_with_tags = pickle.load(open('pp_with_tags.pkl', "rb"))
trained_classifier = joblib.load('classifier_data/linear_svc_classifier.jlb') 
keywords = numpy.array(sorted(list(keywords)))

coefs = np.vstack([e.steps[-1][1].coef_ for e in trained_classifier.estimators_])

import os
import codecs
try:
    os.makedirs("important_keywords/tags")
except OSError, e:
    pass
try:
    os.makedirs("important_keywords/keywords")
except OSError, e:
    pass

doc_in_class = defaultdict(list)

print "creating tag dicts"
for a in pp_with_tags:
    for tag in a['tags']:
        doc_in_class[tag].append(a)



print "creating keyword dict"
keyword_dict = {}
for i,w in enumerate(keywords):
    keyword_dict[w] = i


print "splitting docs"
pp_with_tags = pickle.load(open('pp_with_tags.pkl', "rb"))
pp_dict = {}
for pp in pp_with_tags:
    pp_dict[pp['id']] = pp['text']

def output_tag(class_file, w, estimator_max, estimator_min, weight, hyperlink = False):
    orig_weight = weight
    pre = post = ''
    if weight > 0 and estimator_max != 0:
        weight /= estimator_max
        if weight > 0.05 and hyperlink:
            pre = u"<a href='../tags/" + w.replace(u'/', u' ') + u".html' title='" + str(orig_weight) + u"'>"
            post = u"</a>"
        print >>class_file, pre + u"<span style='color:#00%02X00;'>" % (int(255 * weight),) + w + u"</span>" + post + "&nbsp;"
    elif weight < 0 and estimator_min != 0:
        weight /= estimator_min
        if weight > 0.05 and hyperlink:
            pre = u"<a href='../tags/" + w.replace(u'/', u' ') + u".html' title='" + str(orig_weight) + u"'>"
            post = u"</a>"
        print >>class_file, pre + u"<span style='color:#%02X0000;'>" % (int(255 * weight),) + w + u"</span>" + post + "&nbsp;"
    else:
        print >>class_file, u"<span style='color:#000000;'>" + w + u"</span>&nbsp;"

def output_word(class_file, w, estimator_max, estimator_min, coefs, keyword_dict, hyperlink = False):
    weight = coefs[keyword_dict[w]]
    pre = post = ''
    if weight > 0 and estimator_max != 0:
        weight /= estimator_max
        if weight > 0.05 and hyperlink:
            pre = u"<a href='../keywords/" + w.replace(u'/', u' ') + u".html' title='" + str(coefs[keyword_dict[w]]) + u"'>"
            post = u"</a>"
        print >>class_file, pre + u"<span style='color:#00%02X00;'>" % (int(255 * weight),) + w + u"</span>" + post + "&nbsp;"
    elif weight < 0 and estimator_min != 0:
        weight /= estimator_min
        if weight > 0.05 and hyperlink:
            pre = u"<a href='../keywords/" + w.replace(u'/', u' ') + u".html' title='" + str(coefs[keyword_dict[w]]) + u"'>"
            post = u"</a>"
        print >>class_file, pre + u"<span style='color:#%02X0000;'>" % (int(255 * weight),) + w + u"</span>" + post + "&nbsp;"
    else:
        print >>class_file, u"<span style='color:#000000;'>" + w + u"</span>&nbsp;"


def format_word(w, estimator_max, estimator_min, coefs, keyword_dict, hyperlink = False):
    orig_Weight = weight = coefs[keyword_dict[w]]
    pre = post = ''
    if weight > 0 and estimator_max != 0:
        weight /= estimator_max
        if hyperlink:
            pre = u"<a href='../keywords/" + w.replace(u'/', u' ') + u".html' title='" + str(orig_Weight) + u"'>"
            post = u"</a>"
        v = u"<span style='color:#00%02X00;'>" % (int(255 * weight),) + w + u"</span>"
    elif weight < 0 and estimator_min != 0:
        weight /= estimator_min
        if hyperlink:
            pre = u"<a href='../keywords/" + w.replace(u'/', u' ') + u".html' title='" + str(orig_Weight) + u"'>"
            post = u"</a>"
        v = u"<span style='color:#%02X0000;'>" % (int(255 * weight),) + w + u"</span>"
    else:
        v = u"<span style='color:#000000;'>" + w + u"</span>"
    return u"%s%s%s" % (pre, v, post,)


ATTR_AMOUNT = 10
important_keywords = keywords[numpy.abs(coefs).argsort()[:,-ATTR_AMOUNT:]]

MAX_RE_GROUP = 100
def create_re(estimator_max, estimator_min, coefs, keyword_dict):
    #return ("|".join(p) for p in zip(*(
    #        (
    #            u"(?P<pre_%d>\\b)%s(?P<post_%d>\\b)" % (i, re.escape(k), i, ), 
    #            u"\\g<pre_%d>%s\\g<post_%d>" % (i, re.escape(format_word(k, estimator_max, estimator_min, estimator, keyword_dict, hyperlink = True)), i, ),
    #        )
    #        for i, k 
    #        in enumerate(keywords[numpy.where(estimator.coef_[0] != 0)])
    #    )
    #))

    return {        
        k : format_word(k, estimator_max, estimator_min, coefs, keyword_dict, hyperlink = True)
        for k 
        in keywords[numpy.where(coefs != 0)]

    }
ALLOWED_PRELETTERS = 3
MIN_WORD_LEN = 2
def replace_match(replacements, match):
    whole_match_str = match_str = match.group(0)
    if match_str in replacements:
        return replacements[match_str]

    for i in xrange(1, min(ALLOWED_PRELETTERS + 1, len(match_str) - MIN_WORD_LEN + 1)):
        pre, pre_match_str = match_str[:i], match_str[i:]
        if pre_match_str in replacements:
            return pre + replacements[pre_match_str]

    return u"[%s]" % (match.group(0),)

print "creating files"
for i, (class_name, important_keyword_for_class, estimator) in enumerate(zip(lb.classes_, important_keywords, trained_classifier.estimators_)):
    print "tag", str(i), "/", str(len(lb.classes_))
    class_file = codecs.open("important_keywords/tags/" + class_name.replace("/", ' ') + ".html", "wt", encoding="utf-8")

    print >>class_file, u"<html dir='rtl'><head><title>Keyword Explanation for Class " + class_name + u"</title></head><body><meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>"
    print >>class_file, u"<h1>" + class_name + u"</h1><br/>"
    print >>class_file, u"<h2>Most influencing words</h2>"
    estimator_min, estimator_max = coefs[i,:].min(), coefs[i,:].max()
    for keyword in important_keyword_for_class:
        output_word(class_file, keyword, estimator_max, estimator_min, coefs[i], keyword_dict)
        print >>class_file, u"(", str(coefs[i,keyword_dict[keyword]]), u")<br/>"

#    tag_pattern, tag_replacement_pattern = create_re(estimator_max, estimator_min, estimator, keyword_dict)    
#    tag_re = re.compile(tag_pattern, re.MULTILINE | re.UNICODE)
    replacements = create_re(estimator_max, estimator_min, coefs[i], keyword_dict)
    replacements_re = re.compile('|'.join(('|'.join((u'\\b%s%s\\b' % (u'\\w' * i, p,) for p in replacements.iterkeys())) for i in xrange(ALLOWED_PRELETTERS + 1))), re.UNICODE)
    print >>class_file, u"<table border='1'>"
    for doc in doc_in_class[class_name]:

        print >>class_file, u"<tr><td valign='top'>" + unicode(doc['id']) + u"</td><td valign='top'>"
        print >>class_file, replacements_re.sub(partial(replace_match, replacements), pp_dict[doc['id']])
        
        #import pdb; pdb.set_trace()
#        print >>class_file, reduce(lambda s,(o,r): re.sub(o,r,s, flags=re.UNICODE), replacements, pp_dict[doc['id']])
#        print >>class_file, tag_re.sub(tag_replacement_pattern, pp_dict[doc['id']])
        print >>class_file, u"</td></tr>"
    print >>class_file, u"</table></body></html>"
    class_file.close()

coef_abs = numpy.abs(coefs)
sorted_keywords = coef_abs.argsort(axis = 0)
min_weight, max_weight = coefs.min(axis = 1), coefs.max(axis = 1)
for keyword_count, i in enumerate(coef_abs.sum(axis = 0).argsort()[::-1]):
    keyword = keywords[i]
    print "keyword", str(keyword_count), "/", str(len(keywords)), "(", str(i), ")"
    keyword_file = codecs.open("important_keywords/keywords/" + keyword.replace("/", ' ') + ".html", "wt", encoding="utf-8")
    print >>keyword_file, u"<html dir='rtl'><head><title>Tag Explanation for Keyword " + keyword + u"</title></head><body><meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>"
    print >>keyword_file, u"<h1>" + keyword + u"</h1><br/>"
    print >>keyword_file, u"<h2>Most influenced tags</h2>"
    weights = coefs[:,i]
    class_keywords = sorted_keywords[::-1,i]

    for class_name, weight, max_weight_, min_weight_ in zip(lb.classes_[class_keywords], weights[class_keywords], max_weight[class_keywords], min_weight[class_keywords]):
        if weight != 0:
            output_tag(keyword_file, class_name, max_weight_, min_weight_, weight, hyperlink = True)
            print >>keyword_file, u"<br/>"
    print >>keyword_file, u"</body></html>"
    keyword_file.close()
