#encoding: utf-8
from django.db.models.signals import m2m_changed, post_save
from django.contrib.contenttypes.models import ContentType
from actstream import action
from actstream.models import Action

from utils import cannonize, disable_for_loaddata
from mks.models import Member, Party
from laws.models import PrivateProposal, VoteAction, MemberVotingStatistics,\
    PartyVotingStatistics

def record_bill_proposal(**kwargs):
    if kwargs['action'] != "post_add":
        return
    private_proposal_ct = ContentType.objects.get(app_label="laws", model="privateproposal")
    member_ct = ContentType.objects.get(app_label="mks", model="member")
    proposal = kwargs['instance']
    if str(kwargs['sender']).find('proposers')>=0:
        verb = 'proposed'
    else:
        verb = 'joined'
    for mk_id in kwargs['pk_set']:
        if Action.objects.filter(actor_object_id=mk_id, actor_content_type=member_ct, verb=verb, target_object_id=proposal.id, 
                target_content_type=private_proposal_ct).count()==0:
            mk = Member.objects.get(pk=mk_id)
            action.send(mk, verb=verb, target=proposal, timestamp=proposal.date)

m2m_changed.connect(record_bill_proposal, sender=PrivateProposal.proposers.through)
m2m_changed.connect(record_bill_proposal, sender=PrivateProposal.joiners.through) # same code handles both events

@disable_for_loaddata
def record_vote_action(sender, created, instance, **kwargs):
    if created:
        action.send(instance.member, verb='voted',
                    description=instance.get_type_display(),
                    target = instance.vote,
                    timestamp=instance.vote.time)
post_save.connect(record_vote_action, sender=VoteAction, 
    dispatch_uid='vote_action_record_member' )

@disable_for_loaddata
def handle_party_save(sender, created, instance, **kwargs):
    if created and instance._state.db=='default':
        PartyVotingStatistics.objects.get_or_create(party=instance)
post_save.connect(handle_party_save, sender=Party)

@disable_for_loaddata
def handle_mk_save(sender, created, instance, **kwargs):
    if created and instance._state.db=='default':
        MemberVotingStatistics.objects.get_or_create(member=instance)
post_save.connect(handle_mk_save, sender=Member)

