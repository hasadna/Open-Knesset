import datetime
import urllib
from operator import attrgetter
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.db.models import Count
from piston.handler import BaseHandler
from piston.utils import rc
from knesset.mks.models import Member, Party, Membership
from knesset.laws.models import Vote, VoteAction, Bill, KnessetProposal, GovProposal
from knesset.agendas.models import Agenda
from knesset.committees.models import Committee, CommitteeMeeting
from knesset.links.models import Link
from tagging.models import Tag, TaggedItem
from knesset.events.models import Event
import math
from django.forms import model_to_dict

DEFAULT_PAGE_LEN = 20
class HandlerExtensions():
    ''' a collection of extensions to Piston's `BaseHandler` '''
    @classmethod
    def url(self, a):
        ''' return the url of the objects page on the site '''
        return a.get_absolute_url()

    def limit_by_request(self, request):
        num = int(request.GET.get('num', DEFAULT_PAGE_LEN))
        page = int(request.GET.get('page', 0))
        return self.qs[page*num:(page+1)*num]

class MemberHandler(BaseHandler, HandlerExtensions):
    fields = ('id', 'url', 'gender', 'name','party', 'img_url', 'votes_count',
              'votes_per_month', 'service_time',
              'discipline','average_weekly_presence',
              'committee_meetings_per_month',#'bills',
              'bills_proposed','bills_passed_pre_vote',
              'bills_passed_first_vote','bills_approved',
              'roles', 'average_weekly_presence_rank', 'committees',
              'is_current', 'start_date', 'end_date',
              'phone', 'fax', 'email', 'family_status', 'number_of_children',
              'date_of_birth', 'place_of_birth', 'date_of_death',
              'year_of_aliyah', 'place_of_residence',
              'area_of_residence', 'place_of_residence_lat',
              'place_of_residence_lon', 'residence_centrality',
              'residence_economy', 'current_role_descriptions', 'links')

    allowed_methods = ('GET')
    model = Member
    qs = Member.objects.all()

    @classmethod
    def gender (self, member):
        return member.get_gender_display()

    @classmethod
    def party (self, member):
        return member.current_party.name

    @classmethod
    def votes_count (self, member):
        return member.voting_statistics.votes_count()

    @classmethod
    def votes_per_month (self, member):
        return round(member.voting_statistics.average_votes_per_month(),1)

    @classmethod
    def service_time (self, member):
        return member.service_time()

    @classmethod
    def discipline (self, member):
        x = member.voting_statistics.discipline()
        if x:
            return round(x,2)
        else:
            return None

    #@classmethod
    #def bills(cls, member):
    #    d = [{'title':b.full_title,
    #          'url':b.get_absolute_url(),
    #          'stage':b.stage,
    #          'stage_text':b.get_stage_display(),}
    #        for b in member.bills.all()]
    #    return d

    @classmethod
    def bills_proposed(self, member):
        return member.bills_stats_proposed

    @classmethod
    def bills_passed_pre_vote(self, member):
        return member.bills_stats_pre

    @classmethod
    def bills_passed_first_vote(self, member):
        return member.bills_stats_first

    @classmethod
    def bills_approved(self, member):
        return member.bills_stats_approved

    @classmethod
    def roles (self, member):
        return member.get_role

    @classmethod
    def average_weekly_presence(cls, member):
        return member.average_weekly_presence_hours

    @classmethod
    def average_weekly_presence_rank (self, member):
        ''' Calculate the distribution of presence and place the user on a 5 level scale '''
        SCALE = 5

        rel_location = cache.get('average_presence_location_%d' % member.id)
        if not rel_location:

            presence_list = sorted(map(lambda member: member.average_weekly_presence_hours,
                                       Member.objects.all()))
            presence_groups = int(math.ceil(len(presence_list) / float(SCALE)))

            # Generate cache for all members
            for mk in Member.objects.all():
                avg = mk.average_weekly_presence_hours
                if avg:
                    mk_location = 1 + (presence_list.index(avg) / presence_groups)
                else:
                    mk_location = 0

                cache.set('average_presence_location_%d' % mk.id, mk_location, 60*60*24)

                if mk.id == member.id:
                    rel_location = mk_location

        return rel_location

    @classmethod
    def committees (self, member):
        temp_list = member.committee_meetings.values("committee", "committee__name").annotate(Count("id")).order_by('-id__count')[:5]
        return (map(lambda item: (item['committee__name'], reverse('committee-detail', args=[item['committee']])), temp_list))

    @classmethod
    def links(cls, member):
        ct = ContentType.objects.get_for_model(Member)
        temp_list = Link.objects.filter(active=True,
                                        content_type=ct,
                                        object_pk=member.id).values('title',
                                                                    'url')
        return (map(lambda item: (item['title'], item['url']), temp_list))

    @classmethod
    def member (self, member):
        qs = self.qs.filter(member=member)
        return map(lambda o: dict(url=o.party.get_absolute_url(),
                     name=o.party.name,
                     since=o.start_date,
                     until=o.end_date,
                     ), qs)

    def read(self, request, **kwargs):
        if id not in kwargs and 'q' in request.GET:
            q = request.GET['q']
            q = urllib.unquote(q)
            qs = self.qs
            try:
                q = int(q)
                return qs.filter(pk=q)
            except ValueError:
                return Member.objects.find(q)

        return super(MemberHandler,self).read(request, **kwargs)

class VoteHandler(BaseHandler, HandlerExtensions):
    fields = ('url', 'title', 'time',
              'summary','full_text',
              'for_votes', 'against_votes', 'abstain_votes', 'didnt_vote',
              'agendas','bills',
             )
    exclude = ('member')
    allowed_methods = ('GET',)
    model = Vote
    qs = Vote.objects.all()

    def read(self, request, **kwargs):
        ''' returns a vote or a list of votes '''
        qs = self.qs

        if 'id' in kwargs:
            return super(VoteHandler, self).read(request, **kwargs)

        type = request.GET.get('type', None)
        order = request.GET.get('order', None)
        days_back = request.GET.get('days_back', None)
        page_len = int(request.GET.get('page_len', DEFAULT_PAGE_LEN))
        page_num= int(request.GET.get('page_num', 0))

        if type:
            qs = qs.filter(title__contains=type)
        if days_back:
            qs = qs.filter(time__gte=datetime.date.today()-datetime.timedelta(days=int(days_back)))
        if order:
            qs = qs.sort(by=order)
        return qs[page_len*page_num:page_len*(page_num +1)]

    @classmethod
    def bills(cls, vote):
        return [b.id for b in vote.bills()]

    @classmethod
    def for_votes(self, vote):
        return vote.get_voters_id('for')

    @classmethod
    def against_votes(self, vote):
        return vote.get_voters_id('against')

    @classmethod
    def abstain_votes(self, vote):
        return vote.get_voters_id('abstain')

    @classmethod
    def didnt_vote(self, vote):
        return vote.get_voters_id('no-vote')

    @classmethod
    def agendas(cls, vote):
        # Augment agenda with reasonings from agendavote and
        # arrange it so that it will be accessible using the
        # agenda's id in JavaScript
        agendavotes = vote.agendavotes.all()
        agendas     = [model_to_dict(av.agenda) for av in agendavotes]
        reasonings  = [av.reasoning for av in agendavotes]
        text_scores = [av.get_score_display() for av in agendavotes]
        for i in range(len(agendas)):
            agendas[i].update({'reasoning':reasonings[i], 'text_score':text_scores[i]})
        return dict(zip([a['id'] for a in agendas],agendas))

class BillHandler(BaseHandler, HandlerExtensions):
    # TODO: s/bill_title/title
    fields = ('url', 'bill_title', 'popular_name',
              'stage_text', 'stage_date',
              'votes',
              'committee_meetings',
              'proposing_mks',
              'joining_mks',
              'tags',
              'proposals',
             )

    exclude = ('member')
    allowed_methods = ('GET',)
    model = Bill
    qs = Bill.objects.all()

    def read(self, request, **kwargs):
        ''' returns a bill or a list of bills '''
        qs = self.qs

        if 'id' in kwargs:
            return super(BillHandler, self).read(request, **kwargs)

        type = request.GET.get('type', None)
        order = request.GET.get('order', None)
        days_back = request.GET.get('days_back', None)
        page_len = int(request.GET.get('page_len', DEFAULT_PAGE_LEN))
        page_num= int(request.GET.get('page_num', 0))

        if type:
            qs = qs.filter(title__contains=type)
        if days_back:
            qs = qs.filter(stage_date__gte=datetime.date.today()-datetime.timedelta(days=int(days_back)))
        if order:
            qs = qs.sort(by=order)
        return qs[page_len*page_num:page_len*(page_num +1)]

    @classmethod
    def stage_text(self, bill):
        return bill.get_stage_display()

    @classmethod
    def votes(self, bill):
        pre_votes =   [ {'id': x.id, 'date': x.time, 'description': x.__unicode__(), 'count_for_votes': len(x.get_voters_id('for')), 'count_against_votes': len(x.get_voters_id('against')), 'count_didnt_votes': len(x.get_voters_id('no-vote'))} for x in bill.pre_votes.all()]
        first_vote = None
        if bill.first_vote != None:
            x = bill.first_vote
            first_vote = {'id': x.id, 'date': x.time, 'description': x.__unicode__(), 'count_for_votes': len(x.get_voters_id('for')), 'count_against_votes': len(x.get_voters_id('against')), 'count_didnt_votes': len(x.get_voters_id('no-vote'))}
        approval_vote = None
        if bill.approval_vote != None:
            x = bill.approval_vote
            approval_vote = {'id': x.id, 'date': x.time, 'description': x.__unicode__(), 'count_for_votes': len(x.get_voters_id('for')), 'count_against_votes': len(x.get_voters_id('against')), 'count_didnt_votes': len(x.get_voters_id('no-vote'))}
        all = pre_votes + [first_vote, approval_vote]
        return { 'pre' : pre_votes, 'first' : first_vote, 'approval' : approval_vote, 'all':list(all)}

    @classmethod
    def committee_meetings(self, bill):
        first_committee =   [ {'id': x.id, 'date': x.date, 'description': x.__unicode__()} for x in bill.first_committee_meetings.all() ]
        second_committee = [ {'id': x.id, 'date': x.date, 'description': x.__unicode__()} for x in bill.second_committee_meetings.all() ]
        all = first_committee + second_committee
        #all=set(first_committee+second_committee)
        return { 'first' : first_committee, 'second' : second_committee, 'all':list(all) }

    @classmethod
    def proposing_mks(self, bill):
        return [ { 'id': x.id, 'name' : x.name, 'party' : x.current_party.name, 'img_url' : x.img_url } for x in bill.proposers.all() ]

    @classmethod
    def joining_mks(self, bill):
        return [ { 'id': x.id, 'name' : x.name, 'party' : x.current_party.name,
                  'img_url' : x.img_url } for x in bill.joiners.all() ]

    @classmethod
    def tags(self,bill):
        return [ {'id':t.id, 'name':t.name } for t in bill._get_tags() ]

    @classmethod
    def bill_title(self,bill):
        return u"%s, %s" % (bill.law.title, bill.title)

    @classmethod
    def proposals(self, bill):
        gov_proposal = {}

        try:
            gov_proposal = {'id': bill.gov_proposal.id, 'source_url': bill.gov_proposal.source_url, 'date': bill.gov_proposal.date, 'explanation': bill.gov_proposal.get_explanation()}
        except GovProposal.DoesNotExist:
            pass

        knesset_proposal = {}

        try:
            knesset_proposal = {'id': bill.knesset_proposal.id, 'source_url': bill.knesset_proposal.source_url, 'date': bill.knesset_proposal.date, 'explanation': bill.knesset_proposal.get_explanation()}
        except KnessetProposal.DoesNotExist:
            pass

        return {'gov_proposal': gov_proposal,
                'knesset_proposal': knesset_proposal,
                'private_proposals': [{'id': prop.id, 'source_url': prop.source_url, 'date': prop.date, 'explanation': prop.get_explanation()} for prop in bill.proposals.all()]}



class PartyHandler(BaseHandler):
    fields = ('id', 'name', 'start_date', 'end_date', 'members',
              'is_coalition', 'number_of_seats')
    allowed_methods = ('GET',)
    model = Party

    def read(self, request, **kwargs):
        if id not in kwargs and 'q' in request.GET:
            q = request.GET['q']
            q = urllib.unquote(q)
            return Party.objects.find(q)
        return super(PartyHandler,self).read(request, **kwargs)

    @classmethod
    def members(cls,party):
        return party.members.values_list('id',flat=True)

class TagHandler(BaseHandler):
    fields = ('id', 'name', 'number_of_items')
    allowed_methods = ('GET',)
    model = Tag

    def read(self, request, **kwargs):
        id = None
        if 'id' in kwargs:
            id = kwargs['id']
        if id:
            try:
                return Tag.objects.get(pk=id)
            except Tag.DoesNotExist:
                return rc.NOT_FOUND
        object_id = None
        ctype = None
        if 'object_id' in kwargs and 'object_type' in kwargs:
            object_id = kwargs['object_id']
            try:
                ctype = ContentType.objects.get_by_natural_key(kwargs['app_label'], kwargs['object_type'])
            except ContentType.DoesNotExist:
                pass
        if object_id and ctype:
            tags_ids = TaggedItem.objects.filter(object_id=object_id).filter(content_type=ctype).values_list('tag', flat=True)
            return Tag.objects.filter(id__in=tags_ids)

        vote_tags = Tag.objects.usage_for_model(Vote)
        bill_tags = Tag.objects.usage_for_model(Bill)
        cm_tags = Tag.objects.usage_for_model(CommitteeMeeting)
        all_tags = list(set(vote_tags).union(bill_tags).union(cm_tags))
        all_tags.sort(key=attrgetter('name'))
        return all_tags

    @classmethod
    def number_of_items(self, tag):
        return tag.items.count()

class AgendaHandler(BaseHandler):
    # TODO: Once we have user authentication over the API,
    #       need to expose not only public agendas.
    #       See AgendaManager.get_relevant_for_user(user)
    #       The is true for both read() and number_of_items() methods

    fields = ('id', 'name', 'number_of_items')
    allowed_methods = ('GET',)
    model = Agenda

    def read(self, request, **kwargs):
        agendas = Agenda.objects.get_relevant_for_user(user=None)

        # Handle API calls of type /agenda/[agenda_id]
        id = None
        if 'id' in kwargs:
            id = kwargs['id']
            if id is not None:
                try:
                    return agendas.get(pk=id)
                except Agenda.DoesNotExist:
                    return rc.NOT_FOUND

        # Handle API calls of type /agenda/[app_label]/[vote_id]
        # Used to return the agendas ascribed to a specific vote
        object_id = None
        ctype = None
        if 'object_id' in kwargs and 'object_type' in kwargs:
            object_id = kwargs['object_id']
            try:
                ctype = ContentType.objects.get_by_natural_key(kwargs['app_label'], kwargs['object_type'])
            except ContentType.DoesNotExist:
                pass
            if object_id and (ctype.model == 'vote'):
                return agendas.filter(votes__id=object_id)
        else:
            return agendas

    @classmethod
    def number_of_items(self, agenda):
        return agenda.agendavotes.count()

class CommitteeHandler(BaseHandler, HandlerExtensions):
    fields = ('id',
              'url',
              'name',
              'members',
              'recent_meetings',
              'future_meetings',
             )
    allowed_methods = ('GET',)
    model = Committee

    @classmethod
    def recent_meetings(cls, committee):
        return [ { 'url': x.get_absolute_url(),
                   'title': x.title(),
                   'date': x.date }
                for x in committee.recent_meetings() ]

    @classmethod
    def future_meetings(cls, committee):
        return [ { 'title': x.what,
                   'date': x.when }
                for x in committee.future_meetings() ]

    @classmethod
    def members(cls, committee):
        return [ { 'url': x.get_absolute_url(),
                   'name' : x.name,
                   'presence' : x.meetings_count }
                for x in committee.members_by_presence() ]

class CommitteeMeetingHandler(BaseHandler, HandlerExtensions):
    # fields = ('committee__name', 'url', 'date', 'topics', 'protocol_text', 'src_url',
    fields = (('committee', ('name', 'url')), 'url', 'date', 'topics', 'protocol_text', 'src_url',
              'mks_attended',
              )
    allowed_methods = ('GET',)
    model = CommitteeMeeting

    @classmethod
    def mks_attended(cls, cm):
        return [ { 'url': x.get_absolute_url(),
                   'name': x.name }
                for x in cm.mks_attended.all()]

    def read(self, request, **kwargs):
        ''' returns a meeting or a list of meetings '''
        r = super(CommitteeMeetingHandler, self).read(request, **kwargs)
        if 'id' in kwargs:
            return r
        else:
            self.qs = r
            return self.limit_by_request(request)

class EventHandler(BaseHandler, HandlerExtensions):
    # exclude = ('which_object')
    fields = ( 'which', 'what', 'where', 'when', 'url' )
    allowed_methods = ('GET',)
    model = Event

    def read(self, request, **kwargs):
        ''' returns an event or a list of events '''
        r = super(EventHandler, self).read(request, **kwargs)
        if kwargs and 'id' in kwargs:
            return r
        else:
            return r.filter(when__gte=datetime.datetime.now())

    @classmethod
    def which(cls, event):
        if event.which_object:
            return {
                    'name': unicode(event.which_object),
                    'url': event.which_object.get_absolute_url(),
                    }
        else:
            return None
