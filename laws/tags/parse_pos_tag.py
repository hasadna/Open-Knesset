#!/usr/bin/python
# -*- coding: UTF-8 -*-
import cPickle as pickle

#hebdepparser_path = "/home/o/otadmor/Downloads/hebdepparser"
hebdepparser_path = "/home/someone/hebdepparser"
import subprocess

def parse_lang_tree_popen(text):
#    p = subprocess.Popen(["python", "/home/o/otadmor/Downloads/hebdepparser/parse.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p = subprocess.Popen("python " + hebdepparser_path + "/code/utils/sentences.py | python " + hebdepparser_path + "/parse.py", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    p.stdin.write(text.encode('utf-8'))

    p.stdin.flush()
    p.stdin.close()
    a = p.stdout.read()
    res = ''
    while a != '':
        res += a
        a = p.stdout.read()
    p.stdout.close()
    p.wait()
    return res.decode('utf-8')
    



#    for w in reduce(lambda o, s: o.replace(s, u' '), REMOVE, t).split():

    
import sys
sys.path.append(hebdepparser_path)
from parse import parse_sent
from cStringIO import StringIO
def split_sentences(text):
    for l in reduce(lambda o, s: o.replace(s, s + u'\n'), ['.', '!', '?'], text).splitlines():
        l = l.strip()
        if not l.endswith("."):
            l += "."
        yield l

import codecs
def parse_lang_tree(text):
    out = StringIO()
    for l in split_sentences(text):
        parse_sent(l, out)
    return out.getvalue().decode('utf-8')

pp_with_tags = pickle.load(open('pp_with_tags.pkl', "rb"))

data = []
for i, pp in enumerate(pp_with_tags):
    pp_text, pp_tag, pp_id = pp['text'], pp['tags'], pp['id']
    
    print str(i), "/", str(len(pp_with_tags))
    try:
        parsed_pos = parse_lang_tree(pp_text)
    except:
        import traceback; traceback.print_exc()
        print "at pp", i
        import pdb; pdb.set_trace()
    data.append({'pos' : parsed_pos, 'tags' : pp_tag, 'id' : pp_id})
    
    

pickle.dump(data, open('pp_pos_with_tags.pkl', 'wb'))

