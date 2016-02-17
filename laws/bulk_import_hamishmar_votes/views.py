# encoding: utf-8
from django.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from forms import BulkImportHamishmarVotesForm
from django.views.decorators.csrf import csrf_protect
from django.core.context_processors import csrf
from knesset_data.non_knesset_data.hamishmar_votes import HamishmarVote
from mks.models import Member
from django.shortcuts import resolve_url
import json
from django.utils.html import mark_safe
from laws.models import Vote, VoteAction
from simple.scrapers import hebrew_strftime
from datetime import date, datetime


class OknessetHamishmarVote(HamishmarVote):

    def __init__(self, data):
        super(OknessetHamishmarVote, self).__init__(data)
        ##########################################################################
        # TODO:
        # once https://github.com/hasadna/knesset-data/issues/18 is done
        # the member_id properties will be available
        # until then, we just set fake values here
        # member_ids = self.voted_for_member_ids + self.voted_against_member_ids
        # currently, we can only test fake data
        self.voted_for_member_ids = [90]
        self.voted_against_member_ids = []
        ###########################################################################
        self.num_voted_for = len(self.voted_for_member_names)
        self.num_voted_against = len(self.voted_against_member_names)
        self.errors = self.get_errors()

    def get_errors(self):
        errors = []
        # make sure all member ids are valid and exist in DB
        member_ids = self.voted_for_member_ids + self.voted_against_member_ids
        missing_member_ids = []
        for member_id in member_ids:
            qs = Member.objects.filter(id=str(member_id))
            if not qs.count() == 1:
                missing_member_ids.append(str(member_id))
        if len(missing_member_ids) > 0:
            errors.append('could not find member ids: %s'%','.join(missing_member_ids))
        return errors

    def get_data_for_db_update(self):
        return {
            'voted_for_member_ids': self.voted_for_member_ids,
            'voted_against_member_ids': self.voted_against_member_ids,
            'date': [self.date.year, self.date.month, self.date.day],
            'protocol_url': self.protocol_url,
            'hamishmar_id': self.id,
            'hamishmar_law_id': self.data['Law_ID'],
            'hamishmar_vote_stage': self.data['Vote_stage'],
        }


def add_hamishmar_vote(hamishmar_vote):
    oknesset_vote, error = None, None
    # hamishmar_vote contains the data from OknessetHamishmarVote.get_data_for_db_update
    qs = Vote.objects.filter(src_type='hamishmar', src_id=hamishmar_vote['hamishmar_id'])
    if qs.exists():
        error = 'Vote with Hamishmar id %s already exists'%hamishmar_vote['hamishmar_id']
    else:
        oknesset_vote = Vote.objects.create(
            src_id=hamishmar_vote['hamishmar_id'],
            src_type='hamishmar',
            title=u'הצבעה שמית על הצעת חוק {law_id}'.format(
                law_id=str(hamishmar_vote['hamishmar_law_id'])
            ),
            time_string=u'יום ' + hebrew_strftime(date(*hamishmar_vote['date']), fmt=u'%A %d %B %Y'),
            importance=1,
            time=datetime(*hamishmar_vote['date']),
            # meeting_number='',  # we might be able to determine the meeting number from the protocol url
            # vote_number='',  # there is no vote number
            hamishmar_law_id=hamishmar_vote['hamishmar_law_id'],
            hamishmar_vote_stage=hamishmar_vote['hamishmar_vote_stage'],
            hamishmar_protocol_url=hamishmar_vote['protocol_url']
        )
        for member in [Member.objects.get(pk=member_id) for member_id in hamishmar_vote['voted_for_member_ids']]:
            VoteAction.objects.create(vote=oknesset_vote, member=member, type=u'for', party=member.current_party)
        for member in [Member.objects.get(pk=member_id) for member_id in hamishmar_vote['voted_against_member_ids']]:
            VoteAction.objects.create(vote=oknesset_vote, member=member, type=u'against', party=member.current_party)
        oknesset_vote.update_vote_properties()
    return oknesset_vote, error


@csrf_protect
@staff_member_required
def main(request):
    context = {
        'LANGUAGE_CODE': 'HE',
        'LANGUAGE_BIDI': True,
    }
    if request.method == 'POST':
        if request.POST.has_key('votesData'):
            template_name = "laws/bulk_import_hamishmar_votes/done.html"
            oknesset_votes = []
            errors = []
            for hamishmar_vote in json.loads(request.POST['votesData'])['votes']:
                oknesset_vote, error = add_hamishmar_vote(hamishmar_vote)
                if oknesset_vote:
                    oknesset_votes.append(oknesset_vote)
                if error:
                    errors.append(error)
                if not oknesset_vote and not error:
                    errors.append('unexpected error in hamishmar vote: %s'%hamishmar_vote)
            context.update({
                'msg': '%s votes were added'%len(oknesset_votes),
                'oknesset_votes': oknesset_votes,
                'errors': errors,
                'votes_data_json': mark_safe(request.POST['votesData'])
            })
        else:
            template_name = "laws/bulk_import_hamishmar_votes/approve.html"
            file = request.FILES['file']
            hamishmar_votes = OknessetHamishmarVote.get_from_csv(file)
            votes_data = {'votes': [vote.get_data_for_db_update() for vote in hamishmar_votes]}
            context.update({
                'msg': 'Please review the votes that will be added' if len(hamishmar_votes) > 0 else 'No votes in file',
                'approve_votes': hamishmar_votes,
                'votes_data_json': mark_safe(json.dumps(votes_data))
            })
    else:
        template_name = "laws/bulk_import_hamishmar_votes/start.html"
        context.update({'form': BulkImportHamishmarVotesForm()})
    context.update(csrf(request))
    return render_to_response(template_name, context)
