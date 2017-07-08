# -*- coding: utf-8 -*-

from tagging.models import Tag, TaggedItem
from django.contrib.contenttypes.models import ContentType
from laws.models import Vote, Bill
from committees.models import CommitteeMeeting

import operator


def approve(admin, request, tag_suggestions):
    for tag_suggestion in tag_suggestions:
        obj = tag_suggestion.object

        ct = ContentType.objects.get_for_model(obj)

        tag, t_created = Tag.objects.get_or_create(name=tag_suggestion.name)
        ti, ti_created = TaggedItem.objects.get_or_create(
            tag=tag, object_id=obj.pk, content_type=ct)

        tag_suggestion.delete()


def sum_add_two_dictionaries(dict, dict_to_add):
    """Takes two dictionaries, assuming their values are numeric, and sum each item that exist in both,
    writing the merged dictionary to the first dictionary."""
    # go over the dictionary to add
    for key in dict_to_add:
        if key in dict:
            dict[key] += dict_to_add[key]
        else:
            dict[key] = dict_to_add[key]


# A list of prefix charcters to use in tag extraction
prefixes = [u'ב', u'ו', u'ה', u'מ', u'מה', u'ל', u'']
_all_tags_names = []


def all_tags_names():
    '''Lazy intialization of tags list'''
    global _all_tags_names
    if _all_tags_names == []:
        # Extract only used tags, to avoid irrelevant tags
        vote_tags = Tag.objects.usage_for_model(Vote)
        bill_tags = Tag.objects.usage_for_model(Bill)
        cm_tags = Tag.objects.usage_for_model(CommitteeMeeting)
        all_tags = list(set(vote_tags).union(bill_tags).union(cm_tags))

        # A list of tags that have been tagged over 10 times in the website

        _all_tags_names = [tag.name for tag in all_tags]

    return _all_tags_names


def get_tags_in_text(text):
    """Returns a dictionary, the keys are tags found in text, and the values are the number of occurrences in text"""

    result_dict = {}
    words = text.split() if text is not None else []

    # look for tag in word
    for tag in all_tags_names():
        # create tag variations according to prefixes
        tag_variations = [(p + tag) for p in prefixes]

        # find number of occurences of tags for each word
        occurence_count = 0
        for word in words:
            if word in tag_variations:
                occurence_count += 1

        # if tag found more than once, add them
        if occurence_count > 0:
            result_dict[tag] = result_dict.get(tag, 0) + occurence_count

    return result_dict


def extract_suggested_tags(current_tags, text_list):
    '''Returns a sorted list consisting of key/value tuples where the keys are tags found in arguments' text,
        and the values are the number of occurrences in arguments text.
        current_tags are removed from final list.
        The list is sorted from most occuring tags to least occuring tags'''

    tags_occurrences = {}

    # find occurences of tags in text
    for text_to_extract in text_list:
        sum_add_two_dictionaries(tags_occurrences, get_tags_in_text(text_to_extract))

    # remove tags that are already tagged
    for tag in current_tags:
        if tag.name in tags_occurrences:
            del tags_occurrences[tag.name]

    # sort suggestions
    return sorted(tags_occurrences.iteritems(), key=operator.itemgetter(1), reverse=True)
