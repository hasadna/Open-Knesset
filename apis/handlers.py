import datetime, urllib, math
from operator import attrgetter
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.db.models import Count
from piston.handler import BaseHandler
from piston.utils import rc
from mks.models import Member, Party
from laws.models import Vote, Bill
from agendas.models import Agenda
from committees.models import Committee, CommitteeMeeting
from links.models import Link
from tagging.models import Tag, TaggedItem
from events.models import Event
from django.forms import model_to_dict
import voting
from django.core.exceptions import ObjectDoesNotExist

DEFAULT_PAGE_LEN = 20
class HandlerExtensions(object):
    ''' a collection of extensions to Piston's `BaseHandler` '''
    @staticmethod
    def url(a):
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

    allowed_methods = ('GET',)
    model = Member
    qs = Member.current_knesset.all()

    def queryset(self, request):
        return self.model.current_knesset.all()

    @staticmethod
    def gender(member):
        return member.get_gender_display()

    @staticmethod
    def party(member):
        return member.current_party.name

    @staticmethod
    def votes_count(member):
        return member.voting_statistics.votes_count()

    @staticmethod
    def votes_per_month(member):
        return round(member.voting_statistics.average_votes_per_month, 1)

    @staticmethod
    def service_time(member):
        return member.service_time()

    @staticmethod
    def discipline(member):
        x = member.voting_statistics.discipline()
        if x:
            return round(x, 2)

    #@staticmethod
    #def bills(member):
    #    d = [{'title':b.full_title,
    #          'url':b.get_absolute_url(),
    #          'stage':b.stage,
    #          'stage_text':b.get_stage_display(),}
    #        for b in member.bills.all()]
    #    return d

    @staticmethod
    def bills_proposed(member):
        return member.bills_stats_proposed

    @staticmethod
    def bills_passed_pre_vote(member):
        return member.bills_stats_pre

    @staticmethod
    def bills_passed_first_vote(member):
        return member.bills_stats_first

    @staticmethod
    def bills_approved(member):
        return member.bills_stats_approved

    @staticmethod
    def roles(member):
        return member.get_role

    @staticmethod
    def average_weekly_presence(member):
        return member.average_weekly_presence_hours

    @staticmethod
    def average_weekly_presence_rank(member):
        ''' Calculate the distribution of presence and place the user on a 5 level scale '''
        SCALE = 5.0
        cache_fmt = 'average_presence_location_{}'
        rel_location = cache.get(cache_fmt.format(member.id))
        if not rel_location:

            presence_list = [m.average_weekly_presence_hours for m in Member.objects.all()]
            presence_list.sort()
            presence_groups = int(math.ceil(len(presence_list) / SCALE))

            # Generate cache for all members
            for mk in Member.objects.all():
                avg = mk.average_weekly_presence_hours
                if avg:
                    mk_location = 1 + presence_list.index(avg) / presence_groups
                else:
                    mk_location = 0

                cache.set(cache_fmt.format(mk.id), mk_location, 60*60*24)

                if mk.id == member.id:
                    rel_location = mk_location

        return rel_location

    @staticmethod
    def committees(member):
        temp_list = member.committee_meetings.values("committee", "committee__name").annotate(Count("id")).order_by('-id__count')[:5]
        return [(item['committee__name'], reverse('committee-detail', args=[item['committee']])) for item in temp_list]

    @staticmethod
    def links(member):
        ct = ContentType.objects.get_for_model(Member)
        temp_list = Link.objects.filter(active=True,
                                        content_type=ct,
                                        object_pk=member.id)
        return [(item['title'], item['url']) for item in temp_list.values('title', 'url')]

    @staticmethod
    def member(member):
        qs = MemberHandler.qs.filter(member=member)
        return [{'url':o.party.get_absolute_url(),
                'name':o.party.name,
                'since':o.start_date,
                'until':o.end_date} for o in qs]

    def read(self, request, **kwargs):
        if 'id' not in kwargs and 'q' in request.GET:
            q = urllib.unquote(request.GET['q'])
            try:
                return self.qs.filter(pk=int(q))
            except ValueError:
                return Member.objects.find(q)

        return super(MemberHandler,self).read(request, **kwargs)

class VoteHandler(BaseHandler, HandlerExtensions):
    fields = (
        'url', 'title', 'time',
        'summary','full_text',
        'for_votes', 'against_votes', 'abstain_votes', 'didnt_vote',
        ('agendavotes', (('agenda', ('name', 'image')), 'score', 'importance', 'reasoning'))
        ,'bills')
    exclude = ('member')
    allowed_methods = ('GET',)
    model = Vote
    qs = Vote.objects.all()

    def read(self, request, **kwargs):
        ''' returns a vote or a list of votes '''
        qs = self.qs

        if 'id' in kwargs:
            return super(VoteHandler, self).read(request, **kwargs)

        qtype = request.GET.get('type', None)
        order = request.GET.get('order', None)
        days_back = request.GET.get('days_back', None)
        page_len = int(request.GET.get('page_len', DEFAULT_PAGE_LEN))
        page_num = int(request.GET.get('page_num', 0))

        if qtype:
            qs = qs.filter(title__contains=qtype)
        if days_back:
            qs = qs.filter(time__gte=datetime.date.today() - datetime.timedelta(days=int(days_back)))
        if order:
            qs = qs.sort(by=order)
        return qs[page_len*page_num:page_len*(page_num +1)]

    @staticmethod
    def bills(vote):
        return [b.id for b in vote.bills()]

    @staticmethod
    def for_votes(vote):
        return vote.get_voters_id('for')

    @staticmethod
    def against_votes(vote):
        return vote.get_voters_id('against')

    @staticmethod
    def abstain_votes(vote):
        return vote.get_voters_id('abstain')

    @staticmethod
    def didnt_vote(vote):
        return vote.get_voters_id('no-vote')

    @staticmethod
    def agendas(vote):
        # Augment agenda with reasonings from agendavote and
        # arrange it so that it will be accessible using the
        # agenda's id in JavaScript
        ret = {}
        for av in vote.agendavotes.all():
            agenda = model_to_dict(av.agenda)
            agenda.update({'reasoning':av.reasoning, 'text_score':av.get_score_display()})
            ret[agenda['id']] = agenda
        return ret

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

        qtype = request.GET.get('type', None)
        order = request.GET.get('order', None)
        days_back = request.GET.get('days_back', None)
        page_len = int(request.GET.get('page_len', DEFAULT_PAGE_LEN))
        page_num = int(request.GET.get('page_num', 0))
        slice_range = slice(page_len*page_num, page_len*(page_num +1))
        
        if days_back:
            qs = qs.filter(stage_date__gte=datetime.date.today()-datetime.timedelta(days=int(days_back)))
        if 'popular' not in kwargs:
            if qtype:
                qs = qs.filter(title__contains=qtype)
            if order:
                qs = qs.sort(by=order)

            return qs[slice_range]
        else:
            # we use type to specify if we want positive/negative popular bills, or None for "dont care"
            if qtype not in ['positive', 'negative']:
                qtype = None

            v = voting.models.Vote.objects
            # create the ordered list of bills according to the request
            if qtype is None:
                bill_ids = v.get_popular(Bill)
            else:
                filter_score = {'score__gt':0.5} if qtype == 'positive' else {'score__lt':-0.5}
                bill_ids = v.get_top(Bill, min_tv=2).filter(**filter_score).order_by('-totalvotes')
            return [qs.get(pk=x['object_id']) for x in bill_ids[slice_range]]

    @staticmethod
    def stage_text(bill):
        return bill.get_stage_display()

    @staticmethod
    def votes(bill):
        def get_vote(x):
            return None if x is None else {'id': x.id, 'date': x.time, 'description': x.__unicode__(), 
                    'count_for_votes': len(x.get_voters_id('for')), 'count_against_votes': len(x.get_voters_id('against')),
                    'count_didnt_votes': len(x.get_voters_id('no-vote'))}
        pre_votes = [ get_vote(x) for x in bill.pre_votes.all()]
        first_vote = get_vote(bill.first_vote)
        approval_vote = get_vote(bill.approval_vote)
        all_votes = pre_votes + [first_vote, approval_vote]
        return { 'pre' : pre_votes, 'first' : first_vote, 'approval' : approval_vote, 'all' : all_votes}

    @staticmethod
    def committee_meetings(bill):
        def get_commitee(com):
            return [ {'id': x.id, 'date': x.date, 'description': x.__unicode__()} for x in com.all() ]
        first_committee =  get_commitee(bill.first_committee_meetings)
        second_committee = get_commitee(bill.second_committee_meetings)
        #all=set(first_committee+second_committee)
        return { 'first' : first_committee, 'second' : second_committee, 'all' : first_committee + second_committee }

    @staticmethod
    def _get_mksdetails_from(qs):
        return [ { 'id': x.id, 'name' : x.name, 'party' : x.current_party.name, 'img_url' : x.img_url } for x in qs ]

    @staticmethod
    def proposing_mks(bill):
        return BillHandler._get_mksdetails_from(bill.proposers.all())

    @staticmethod
    def joining_mks(bill):
        return BillHandler._get_mksdetails_from(bill.joiners.all())

    @staticmethod
    def tags(bill):
        return [ {'id':t.id, 'name':t.name } for t in bill._get_tags() ]

    @staticmethod
    def bill_title(bill):
        return u"{}, {}".format(bill.law.title, bill.title)
    
    @staticmethod
    def proposals(bill):
        def get_ignore(proposal=None, field=''):
            if not proposal: 
                try:
                    proposal = getattr(bill, field)
                except ObjectDoesNotExist:
                    return {}
            return {'id': proposal.id, 'source_url': proposal.source_url,
                 'date': proposal.date, 'explanation': proposal.get_explanation()}
            
        res = {f:get_ignore(field=f) for f in ('gov_proposal', 'knesset_proposal')}
        res['private_proposals'] = [get_ignore(prop) for prop in bill.proposals.all()]
        return res

class PartyHandler(BaseHandler):
    fields = ('id', 'name', 'start_date', 'end_date', 'members',
              'is_coalition', 'number_of_seats')
    allowed_methods = ('GET',)
    model = Party

    def read(self, request, **kwargs):
        if 'id' not in kwargs and 'q' in request.GET:
            q = urllib.unquote(request.GET['q'])
            return Party.objects.find(q)
        return super(PartyHandler,self).read(request, **kwargs)

    @staticmethod
    def members(party):
        return party.members.values_list('id',flat=True)


def read_helper(getter, success_case, fail_case, kwargs):
    # Handle API calls of type /agenda/[agenda_id]
    try:
        return getter.get(pk=kwargs['id'])
    except ObjectDoesNotExist:
        return rc.NOT_FOUND
    except KeyError:
        pass
    
    # Handle API calls of type /agenda/[app_label]/[vote_id]
    # Used to return the agendas ascribed to a specific vote
    try:
        object_id = kwargs['object_id']
        ctype = ContentType.objects.get_by_natural_key(kwargs['app_label'], kwargs['object_type'])
    except ContentType.DoesNotExist:  pass
    except KeyError:                  pass
    else:
        return success_case(object_id, ctype)
    return fail_case()

class TagHandler(BaseHandler):
    fields = ('id', 'name', 'number_of_items')
    allowed_methods = ('GET',)
    model = Tag

    def read(self, request, **kwargs):
        def success_case(object_id, ctype):
            tags_ids = TaggedItem.objects.filter(object_id=object_id, content_type=ctype) \
                            .values_list('tag', flat=True)
            return Tag.objects.filter(id__in=tags_ids)
        
        def fail_case():
            all_tags = [Tag.objects.usage_for_model(x) for x in (Vote, Bill, CommitteeMeeting)]
            return sorted(set().union(*all_tags), key=attrgetter('name'))
        return read_helper(Tag.objects, success_case, fail_case, kwargs)
    
    @staticmethod
    def number_of_items(tag):
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
        def success_case(object_id, ctype):
            if ctype.model == 'vote':
                return agendas.filter(votes__id=object_id)
            return agendas
        
        def fail_case():
            return agendas
        
        return read_helper(agendas, success_case, fail_case, kwargs)

    @staticmethod
    def number_of_items(agenda):
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

    @staticmethod
    def recent_meetings(committee):
        return [ { 'url': x.get_absolute_url(),
                   'title': x.title,
                   'date': x.date }
                for x in committee.recent_meetings() ]

    @staticmethod
    def future_meetings(committee):
        return [ { 'title': x.what,
                   'date': x.when }
                for x in committee.future_meetings() ]

    @staticmethod
    def members(committee):
        return [ { 'url': x.get_absolute_url(),
                   'name' : x.name,
                   'presence' : x.meetings_percentage }
                for x in committee.members_by_presence() ]

class CommitteeMeetingHandler(BaseHandler, HandlerExtensions):
    # fields = ('committee__name', 'url', 'date', 'topics', 'protocol_text', 'src_url',
    fields = (('committee', ('name', 'url')), 'url', 'date', 'topics', 'protocol_text', 'src_url',
              'mks_attended',
              )
    allowed_methods = ('GET',)
    model = CommitteeMeeting

    @staticmethod
    def mks_attended(cm):
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
        if 'id' in kwargs:
            return r
        return r.filter(when__gte=datetime.datetime.now())

    @staticmethod
    def which(event):
        if event.which_object:
            return {'name': unicode(event.which_object),
                    'url': event.which_object.get_absolute_url() }
