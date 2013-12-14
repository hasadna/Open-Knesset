#encoding: utf-8
import json

from django import template
from django.conf import settings


register = template.Library()

@register.inclusion_tag('laws/bill_full_name.html')
def bill_full_name(bill):
    return { 'bill': bill }

@register.inclusion_tag('laws/bill_list_item.html')
def bill_list_item(bill, add_li=True, show_tags=True):
    return { 'bill': bill, 'add_li': add_li, 'show_tags': show_tags }

@register.inclusion_tag('laws/item_tags.html')
def item_tags(tags):
    return { 'tags': tags }

def split_member_vote_list_by_party(member_vote_list):
    ''' create a party partitioned list of "for" voters and "against" voters '''

    list_by_party = []
    if len(member_vote_list) > 0:
        ''' first party, first member '''
        curr_party = { 'party' : member_vote_list[0].member.current_party.name,
                      'members' : []}
        for vote in member_vote_list:
            member = {'name' : vote.member.name,
                      'url' : vote.member.get_absolute_url(),
                      'img_url' : vote.member.img_url,
                      'id' : vote.member.id}
            if vote.member.current_party.name == curr_party['party']:
                curr_party['members'].append(member)
            else:
                list_by_party.append(curr_party)
                curr_party = { 'party' : vote.member.current_party.name,
                      'members' : [member]}
        ''' last party '''
        list_by_party.append(curr_party)
    return list_by_party

def create_vote_dict(vote):
    for_vote_sorted = vote.for_votes()\
                          .order_by('member__current_party')\
                          .select_related('member','member__current_party')
    for_vote_sorted = list(for_vote_sorted)
    for_votes_grouped = split_member_vote_list_by_party(for_vote_sorted)
    against_vote_sorted = vote.against_votes()\
                              .order_by('member__current_party')\
                              .select_related('member','member__current_party')
    against_vote_sorted = list(against_vote_sorted)
    against_votes_grouped = split_member_vote_list_by_party(against_vote_sorted)

    vote_drill_data = dict({'against': dict({'count': len(against_vote_sorted),
                                          'votes' : against_votes_grouped}),
                            'for': dict({ 'count' : len(for_vote_sorted),
                                          'votes' : for_votes_grouped})})

    vote_dict = dict({'vote' : vote,
                          'vote_drill_data' : json.dumps(vote_drill_data),
                          'vote_passed' : vote.for_votes_count > vote.against_votes_count,
                          'vote_time' : {'day' : vote.time.day,
                           'month' : vote.time.month,
                           'year' : vote.time.year}})
    return vote_dict

def get_explanation(bill, proposals):

    if hasattr(bill, 'knesset_proposal'):
        if bill.knesset_proposal.get_explanation() != '':
            return bill.knesset_proposal.get_explanation()

    if hasattr(bill, 'gov_proposal'):
        if bill.gov_proposal.get_explanation() != '':
            return bill.gov_proposal.get_explanation()

    for proposal in proposals:
        if proposal.get_explanation() != '':
            return proposal.get_explanation()


@register.inclusion_tag('laws/bill_inabox.html')
def bill_inabox(bill):
    """ TODO: firstX and not first3"""
    proposals = list(bill.proposals.all())

    proposers = bill.proposers.all()
    bill_inabox_dict = {
        'bill': bill,
        'billurl': 'http://oknesset.org%s' % bill.get_absolute_url(),
        'proposers_first3': proposers[:3],
        'proposers_count_minus3': len(proposers) - 3,
        'explanation': get_explanation(bill, proposals),
    }

    #proposal
    if proposals:
        proposal = proposals[-1]
        bill_inabox_dict['proposal'] = dict({'day' : proposal.date.day,
                           'month' : proposal.date.month,
                           'year' : proposal.date.year})


    #pre vote
    pre_votes = list(bill.pre_votes.all())
    pre_vote = None
    if pre_votes:
        pre_vote = pre_votes[-1]
        bill_inabox_dict['pre_vote'] = create_vote_dict(pre_vote)

    #first_committee_meetings
    cms = list(bill.first_committee_meetings.all())
    if cms:
        first_committee_meetings = cms[-1]
        bill_inabox_dict['first_committee_meetings'] = dict({'day' : first_committee_meetings.date.day,
                           'month' : first_committee_meetings.date.month,
                           'year' : first_committee_meetings.date.year,
                           'url' : first_committee_meetings.get_absolute_url()})

    #first vote
    fv = bill.first_vote
    if fv:
        bill_inabox_dict['first_vote'] = create_vote_dict(fv)

    #second_committee_meetings
    cms = list(bill.second_committee_meetings.all())
    if cms:
        second_committee_meetings = cms[-1]
        bill_inabox_dict['second_committee_meetings'] = dict({'day' : second_committee_meetings.date.day,
                           'month' : second_committee_meetings.date.month,
                           'year' : second_committee_meetings.date.year,
                           'url' : second_committee_meetings.get_absolute_url()})


    #second+third vote (approval_vote)
    av = bill.approval_vote
    if av:
        bill_inabox_dict['approval_vote'] = create_vote_dict(av)

    return bill_inabox_dict
