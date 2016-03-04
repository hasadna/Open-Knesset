#!/usr/bin/python
# -*- coding: UTF-8 -*-

from BeautifulSoup import BeautifulSoup

import cPickle as pickle

from tag_rename import change_docs_tags, class_map

similar_texts = [
    u"הצעת חוק דומה בעיקרה הונחה",
    u"הצעת חוק זהה הונחה",
    u"הצעות חוק דומות בעיקרן הונחו",
    u"הצעות חוק זהות הונחו",
    u"הצעות חוק זהות הונחו",
    u"הצעת חוק זהות הונחו",
    u"הצעת חוק זהות הונחו",
    u"הצעת חוק זהה הוגשה",
    u"הצעת חוק זהה הונח",
    u"הצעת חוק יסוד זהה הונחה",
    u"הצעת חוק זהה הוגשה",
    u"הצעות חוק זהות הונחו",
    u"הצעת חוק זהות הונחו",
    u"הצעות חוק זהות הונחו",
    u"הצעות חוק זהות הונחו",
    u"הצעות חוק זהות הונחו",
    u"סעיפי הצעת חוק זו מבוססים",
    u"הצעת החוק נכתבה בסיוע",
    u"הצעת חוק דומות הונחו",
    u"הצעת חוק דומה בעיקרה זהה הוגשה",
    u"הצעות חוק זהות הונחו",
    u"הצעות חוק זהות הונחו",
    u"הצעות חוק דומות הונחו",
    u"הצעת חוק-יסוד זהה הונחה",
    u"הצעות חוק-יסוד זהות הונחו",
    u"הצעות חוק זהות הונחו",
    u"הצעת חוק דומה בעיקרה זהה הוגשה",
    u"הצעות חוק זהות הונחה",
    u"הצעת חוק דומות בעיקרן הונחו",
    u"הצעת חוק דומות בעיקרן הונחו",
    u"הצעת דומה בעיקרה הונחה",
    u"הצעות חוק דומות בעיקרון הונחו",
    u"הצעות חוק זהה הונחה",
    u"הצעת חוק דומות בעיקרן הונחן",
    u"הצעת חוק זו הוכנה בסיוע",
    u"הצעת חוק דומות בעיקרן הונחו",

]
pp_without_tags = []
pp_with_tags = []


for i, pp in enumerate(pickle.load(open('pps.pkl', 'rb'))):
    content_html = pp['content_html']
    parsed_html = BeautifulSoup(content_html)
    
    current_tag = parsed_html.find('p', attrs={'class':'explanation-header'})
    if current_tag is None:
        print "no text for pp", pp['id']
        continue
    current_tag = current_tag.findNext()
    text = ''
    while current_tag is not None and '---' not in current_tag.text:
        
        text += current_tag.text
        current_tag = current_tag.findNext()

    tags = [class_map.get(t, t) for t in pp['tags']]

    if pp['id'] in change_docs_tags:
        tags = [change_docs_tags[pp['id']]]
    
    for similar_text in similar_texts:
        similar_loc = text.find(similar_text)
        if similar_loc != -1:
            text = text[:similar_loc]
            
    
    
    if len(tags) == 0:
        pp_without_tags.append({'text' : text, 'id' : pp['id']})
    else:
        pp_with_tags.append({'text' : text, 'id' : pp['id'], 'tags' : tags})
        
        
pickle.dump(pp_without_tags, open("pp_without_tags.pkl", "wb"))
pickle.dump(pp_with_tags, open("pp_with_tags.pkl", "wb"))
    
