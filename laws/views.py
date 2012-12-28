#encoding: utf-8
import urllib, urllib2, difflib, logging, datetime
from time import mktime
from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext as _
from django.utils import simplejson as json
from django.views.generic.list_detail import object_list, object_detail
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseBadRequest
from django.db.models import Count, Q
from django.db import IntegrityError
from django.shortcuts import render_to_response, get_object_or_404
from django.template import loader, RequestContext
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator

from tagging.models import Tag, TaggedItem
from tagging.views import tagged_object_list
from tagging.utils import get_tag
import tagging
import voting
from actstream import action
from knesset.utils import limit_by_request, notify_responsible_adult
from mks.models import Member
from tagvotes.models import TagVote
from hashnav import DetailView, ListView
from agendas.models import Agenda,UserSuggestedVote
from auxiliary.views import CsvView
from forms import VoteSelectForm, BillSelectForm
from models import *

logger = logging.getLogger("open-knesset.laws.views")

def bill_tags_cloud(request, min_posts_count=1):
    member = None
    if 'member' in request.GET:
        member = get_object_or_404(Member, pk=request.GET['member'])
        tags_cloud = Tag.objects.usage_for_queryset(member.bills.all(),counts=True)
        tags_cloud = tagging.utils.calculate_cloud(tags_cloud)
        title = _('Bills by %(member)s by tag') % {'member':member.name}
    else:
        title = _('Bills by tag')
        tags_cloud = Tag.objects.cloud_for_model(Bill)
    return render_to_response("laws/bill_tags_cloud.html",
        {"tags_cloud": tags_cloud, "title":title, "member":member}, context_instance=RequestContext(request))

def bill_tag(request, tag):
    tag_instance = get_tag(tag)
    if tag_instance is None:
        raise Http404(_('No Tag found matching "%s".') % tag)

    extra_context = {'tag':tag_instance}
    extra_context['tag_url'] = reverse('bill-tag',args=[tag_instance])
    if 'member' in request.GET:
        try:
            member_id = int(request.GET['member'])
        except ValueError:
            raise Http404(_('No Member found matching "%s".') % request.GET['member'])
        extra_context['member'] = get_object_or_404(Member, pk=request.GET['member'])
        extra_context['member_url'] = reverse('member-detail',args=[extra_context['member'].id])
        extra_context['title'] = _('Bills tagged %(tag)s by %(member)s') % {'tag': tag, 'member':extra_context['member'].name}
        qs = extra_context['member'].bills.all()
    else: # only tag is given
        extra_context['title'] = _('Bills tagged %(tag)s') % {'tag': tag}
        qs = Bill

    queryset = TaggedItem.objects.get_by_model(qs, tag_instance)
    bill_proposers = [b.proposers.all() for b in TaggedItem.objects.get_by_model(Bill, tag_instance)]
    d = {}
    for bill in bill_proposers:
        for p in bill:
            d[p] = d.get(p,0)+1
    # now d is a dict: MK -> number of proposals in this tag
    mks = d.keys()
    for mk in mks:
        mk.count = d[mk]
    mks = tagging.utils.calculate_cloud(mks)
    extra_context['members'] = mks
    return object_list(request, queryset,
    #return tagged_object_list(request, queryset_or_model=qs, tag=tag,
        template_name='laws/bill_list_by_tag.html', extra_context=extra_context)

def bill_auto_complete(request):
    if request.method != 'GET':
        raise Http404

    if not 'query' in request.GET:
        raise Http404

    options = Bill.objects.filter(full_title__icontains=request.GET['query'])[:30]
    data = []
    suggestions = []
    for i in options:
        data.append(i.id)
        suggestions.append(i.full_title)

    result = { 'query': request.GET['query'], 'suggestions':suggestions, 'data':data }

    return HttpResponse(json.dumps(result), mimetype='application/json')

def vote_tags_cloud(request, min_posts_count=1):
    member = None
    if 'member' in request.GET:
        member = get_object_or_404(Member, pk=request.GET['member'])
        tags_cloud = Tag.objects.usage_for_queryset(member.votes.all(),counts=True)
        tags_cloud = tagging.utils.calculate_cloud(tags_cloud)
        title = _('Votes by %(member)s by tag') % {'member':member.name}
    else:
        title = _('Votes by tag')
        tags_cloud = Tag.objects.cloud_for_model(Vote)
    return render_to_response("laws/vote_tags_cloud.html",
        {"tags_cloud": tags_cloud, "title":title, "member":member}, context_instance=RequestContext(request))

def vote_tag(request, tag):
    tag_instance = get_tag(tag)
    if tag_instance is None:
        raise Http404(_('No Tag found matching "%s".') % tag)

    extra_context = {'tag':tag_instance}
    extra_context['tag_url'] = reverse('vote-tag',args=[tag_instance])
    if 'member' in request.GET:
        extra_context['member'] = get_object_or_404(Member, pk=request.GET['member'])
        extra_context['member_url'] = reverse('member-detail',args=[extra_context['member'].id])
        extra_context['title'] = ugettext_lazy('Votes tagged %(tag)s by %(member)s') % {'tag': tag, 'member':extra_context['member'].name}
        qs = extra_context['member'].votes.all()
    else: # only tag is given
        extra_context['title'] = ugettext_lazy('Votes tagged %(tag)s') % {'tag': tag}
        qs = Vote

    queryset = TaggedItem.objects.get_by_model(qs, tag_instance)
    vote_attendence = [v.votes.all() for v in TaggedItem.objects.get_by_model(Vote, tag_instance)]
    d = {}
    for vote in vote_attendence:
        for v in vote:
            d[v] = d.get(v,0)+1
    # now d is a dict: MK -> number of votes in this tag
    mks = d.keys()
    if mks:
        for mk in mks:
            mk.count = d[mk]
        average = float(sum([mk.count for mk in mks]))/len(mks)
        mks = [mk for mk in mks if mk.count>=average]
        mks = tagging.utils.calculate_cloud(mks)
        extra_context['members'] = mks
    if request.user.is_authenticated():
        extra_context['watched_members'] = \
            request.user.get_profile().members
    else:
        extra_context['watched_members'] = False

    return object_list(request, queryset,
    #return tagged_object_list(request, queryset_or_model=qs, tag=tag,
        template_name='laws/vote_list_by_tag.html', extra_context=extra_context)



def votes_to_bar_widths(v_count, v_for, v_against):
    """ a helper function to compute presentation widths for user votes bars.
        v_count - the total votes count
        v_for - votes for
        v_against - votes against
        returns: a tuple (width of for bar, width of against bar) in percent

    """
    m = 12 # minimal width for small bar
    T = 96 # total width for the 2 bars
    if v_count: # use votes/count, with margin m
        width_for = min(max(int(float(v_for) / v_count * T), m), 100-m)
    else: # 0 votes, use 50:50 width
        width_for = round(T/2)
    width_against = T-width_for
    return (width_for, width_against)

class BillCsvView(CsvView):
    model = Bill
    filename = 'bills.csv'
    list_display = (('full_title', _('Full Title')),
                    ('popular_name', _('Popular Name')),
                    ('get_stage_display', _('Stage')),
                    ('stage_date', _('Stage Date')),
                    ('pre_votes', _('Pre-Votes')),
                    ('first_committee_meetings', _('First Committee Meetings')),
                    ('first_vote', _('First Vote')),
                    ('second_committee_meetings', _('Second Committee Meetings')),
                    ('approval_vote', _('Approval Vote')),
                    ('proposers', _('Proposers')),
                    ('joiners', _('Joiners')))
    
    def community_meeting_gen(self, obj, attr):
        '''
        A helper function to compute presentation of community meetings url list, space separated
        : param obj: The object instance
        : param attr: The object attribute
        
        : return : A string with the urls comma-separated
        '''
        host = self.request.build_absolute_uri("/")
        return " ".join(host + row.get_absolute_url() for row in getattr(obj, attr).all())
    
    def members_gen(self, obj, attr):
        '''
        A helper function to compute presentation of members, comma separated
        : param obj: The object instance
        : param attr: The object attribute
        
        : return : A string with the urls comma-separated
        '''
        return ", ".join(row.name for row in getattr(obj, attr).all())
    
    def proposers(self, obj, attr):
        return self.members_gen(obj ,attr)

    def joiners(self, obj, attr):
        return self.members_gen(obj, attr)

    def first_committee_meetings(self, obj, attr):
        return self.community_meeting_gen(obj, attr)
    
    def second_committee_meetings(self, obj, attr):
        return self.community_meeting_gen(obj, attr)
    
    def pre_votes(self, obj, attr):
        return self.community_meeting_gen(obj, attr)
    
class BillDetailView (DetailView):
    allowed_methods = ['get', 'post']
    model = Bill

    def get_object(self):
        try:
            return super(BillDetailView, self).get_object()
        except Http404:
            self.slug_field = "popular_name_slug"
            return super(BillDetailView, self).get_object()

    def get_context_data(self, *args, **kwargs):
        context = super(BillDetailView, self).get_context_data(*args, **kwargs)
        bill = context['object']
        if bill.popular_name:
            context["keywords"] = bill.popular_name
        if self.request.user.is_authenticated():
            userprofile = self.request.user.get_profile()
            context['watched'] = bill in userprofile.bills
        else:
            context['watched'] = False
            userprofile = None

        # compute data for user votes on this bill
        context['proposers'] = bill.proposers.select_related('current_party')
        votes = voting.models.Vote.objects.get_object_votes(bill)
        if 1 not in votes: votes[1] = 0
        if -1 not in votes: votes[-1] = 0
        count = votes[1] + votes[-1]
        score = {'for': votes[1],
                 'against': votes[-1],
                 'total': votes[1] - votes[-1],
                 'count': count}
        (score['for_percent'], score['against_percent']) = votes_to_bar_widths(
            count, score['for'], score['against'])

        # Count only votes by users that are members of parties
        party_member_votes = voting.models.Vote.objects.get_for_object(
                    bill).filter(user__profiles__party__isnull=False,
                                 is_archived=False)
        votes_for = party_member_votes.filter(direction=1).count()
        votes_against = party_member_votes.filter(direction=-1).count()
        count = votes_for + votes_against
        party_voting_score = {'for': votes_for, 'against': votes_against,
                              'total': votes_for - votes_against,
                              'count': count}
        (party_voting_score['for_percent'], party_voting_score['against_percent']) = votes_to_bar_widths(
            count, party_voting_score['for'], party_voting_score['against'])

        # Count only votes by users that are members of the party of the viewing
        # user
        if userprofile and userprofile.party:
            user_party_member_votes = voting.models.Vote.objects.get_for_object(
                        bill).filter(user__profiles__party=userprofile.party,
                                     is_archived=False)
            votes_for = user_party_member_votes.filter(direction=1).count()
            votes_against = user_party_member_votes.filter(direction=-1).count()
            count = votes_for + votes_against
            user_party_voting_score = {'for': votes_for, 'against': votes_against,
                                       'total': votes_for - votes_against,
                                       'count': count}
            (user_party_voting_score['for_percent'],
             user_party_voting_score['against_percent']) = votes_to_bar_widths(
                count, user_party_voting_score['for'], user_party_voting_score['against'])
        else:
            user_party_voting_score = None


        context['voting_score'] = score
        context['party_voting_score'] = party_voting_score
        context['user_party_voting_score'] = user_party_voting_score
        context['tags'] = list(bill.tags)
        return context

    @method_decorator(login_required)
    def post(self, request, **kwargs):

        object_id = kwargs['pk']
        if not object_id:
            return HttpResponseBadRequest()


        vote = None
        bill = get_object_or_404(Bill, pk=object_id)
        user_input_type = request.POST.get('user_input_type')
        if user_input_type == 'approval vote':
            vote = Vote.objects.get(pk=request.POST.get('vote_id'))
            bill.approval_vote = vote
            bill.update_stage()
        if user_input_type == 'first vote':
            vote = Vote.objects.get(pk=request.POST.get('vote_id'))
            bill.first_vote = vote
            bill.update_stage()
        if user_input_type == 'pre vote':
            vote = Vote.objects.get(pk=request.POST.get('vote_id'))
            bill.pre_votes.add(vote)
            bill.update_stage()

        action.send(request.user, verb='added-vote-to-bill',
                description=vote,
                target=bill,
                timestamp=datetime.datetime.now())
        return HttpResponseRedirect(".")

_('added-vote-to-bill')

@login_required
def bill_unbind_vote(request, object_id, vote_id):
    try:
        bill = Bill.objects.get(pk=object_id)
        vote = Vote.objects.get(pk=vote_id)
    except ObjectDoesNotExist:
        raise Http404
    if request.method == 'POST': # actually unbind
        explanation = request.POST.get('explanation','')
        msg = u'%s is unbinding vote %s from bill %s. explanation: %s' % \
                (str(request.user).decode('utf8'),
                 vote_id,
                 object_id,
                 explanation)
        notify_responsible_adult(msg)

        logger.info(msg)
        if vote in bill.pre_votes.all():
            bill.pre_votes.remove(vote)
        if vote == bill.first_vote:
            bill.first_vote = None
        if vote == bill.approval_vote:
            bill.approval_vote = None
        bill.update_stage(force_update=True)
        return HttpResponseRedirect(reverse('bill-detail', args=[object_id]))
    else: # approve unbind
        context = RequestContext (request,
                                  {'object': bill, 'vote':vote})
        return render_to_response("laws/bill_unbind_vote.html", context)


class BillListView (ListView):

    friend_pages = [
            ('stage','all',_('All stages')),
    ]
    friend_pages.extend([('stage',x[0],_(x[1])) for x in BILL_STAGE_CHOICES])

    bill_stages_names = { 'proposed':_('(Bills) proposed'),
                          'pre':_('(Bills) passed pre-vote'),
                          'first':_('(Bills) passed first vote'),
                          'approved':_('(Bills) approved'),
                        }

    def get_queryset(self):

        member = self.request.GET.get('member', False)
        options = {}
        if member:
            try:
                member = int(member)
            except ValueError:
                raise Http404(_('Invalid member id'))
            member = get_object_or_404(Member, pk=member)
            qs = member.bills
        else:
            qs = Bill.objects

        form = self._get_filter_form()

        if form.is_bound and form.is_valid():
            options = form.cleaned_data

        return qs.filter_and_order(**options)

    def _get_filter_form(self):
        form = BillSelectForm(self.request.GET) if self.request.GET \
                else BillSelectForm()
        return form

    def get_context(self):
        context = super(BillListView, self).get_context()
        r = [['?%s=%s'% (x[0],x[1]),x[2],False,x[1]] for x in self.friend_pages]
        stage = self.request.GET.get('stage', False)
        booklet = self.request.GET.get('booklet', False)
        member = self.request.GET.get('member', False)
        if stage and stage!='all':
            for x in r:
                if x[3]==stage:
                    x[2] = True
                    break
            if stage in self.bill_stages_names:
                context['stage'] = self.bill_stages_names.get(stage)
                context['title'] = _('Bills %(stage)s') % {'stage':context['stage']}
        elif booklet:
            context['title']=_('Bills published in knesset booklet number %s') % booklet
        else:
            r[0][2] = True
        if member:
            context['member'] = get_object_or_404(Member, pk=member)
            context['member_url'] = reverse('member-detail',args=[context['member'].id])
            if stage in self.bill_stages_names:
                context['title'] = _('Bills %(stage)s by %(member)s') % {'stage': self.bill_stages_names[stage], 'member':context['member'].name}
            else:
                context['title'] = _('Bills by %(member)s') % {'member':context['member'].name}

        context['friend_pages'] = r
        context['form'] = self._get_filter_form()
        return context

class VoteListView(ListView):

    def get_queryset(self, **kwargs):
        form = self._get_filter_form()

        if form.is_bound and form.is_valid():
            options = form.cleaned_data
        else:
            options = {}

        return Vote.objects.filter_and_order(**options)

    def _get_filter_form(self):
        form = VoteSelectForm(self.request.GET) if self.request.GET \
                else VoteSelectForm()
        return form

    def get_context(self):
        context = super(VoteListView, self).get_context()

        if self.request.user.is_authenticated():
            context['watched_members'] = \
                self.request.user.get_profile().members
        else:
            context['watched_members'] = False

        context['form'] = self._get_filter_form()
        context['query_string'] = self.request.META['QUERY_STRING']
        return context


class VoteCsvView(CsvView):
    model = Vote
    filename = 'votes.csv'
    list_display = (('title', _('Title')),
                    ('vote_type', _('Vote Type')),
                    ('time', _('Time')),
                    ('votes_count', _('Votes Count')),
                    ('for_votes_count', _('For')),
                    ('against_votes_count', _('Against')),
                    ('against_party', _('Votes Against Party')),
                    ('against_coalition', _('Votes Against Coalition')),
                    ('against_opposition', _('Votes Against Opposition')),
                    ('against_own_bill', _('Votes Against Own Bill')))

    def get_queryset(self, **kwargs):
        form = VoteSelectForm(self.request.GET or {})

        if form.is_bound and form.is_valid():
            options = form.cleaned_data
        else:
            options = {}

        return Vote.objects.filter_and_order(**options)


class VoteDetailView(DetailView):
    model = Vote
    template_resource_name = 'vote'

    def get_context_data(self, *args, **kwargs):
        context = super(VoteDetailView, self).get_context_data(*args, **kwargs)
        vote = context['vote']

        related_bills = list(vote.bills_pre_votes.all())
        if Bill.objects.filter(approval_vote=vote).count()>0:
            related_bills.append(vote.bill_approved)
        if Bill.objects.filter(first_vote=vote).count()>0:
            related_bills.extend(vote.bills_first.all())

        for_votes = vote.for_votes().select_related('member','member__current_party')
        against_votes = vote.against_votes().select_related('member','member__current_party')

        try:
            next_v = vote.get_next_by_time()
            next_v = next_v.get_absolute_url()
        except Vote.DoesNotExist:
            next_v = None
        try:
            prev_v = vote.get_previous_by_time()
            prev_v = prev_v.get_absolute_url()
        except Vote.DoesNotExist:
            prev_v = None

        c = {'title':vote.title,
             'bills':related_bills,
             'for_votes':for_votes,
             'against_votes':against_votes,
             'next_v':next_v,
             'prev_v':prev_v,
             'tags':vote.tags,
            }
        context.update(c)
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        object_id = kwargs['pk']
        try:
            object_id = int(kwargs['pk'])
        except:
            return HttpResponseBadRequest()
        user_input_type = request.POST.get('user_input_type',None)
        vote = get_object_or_404(Vote, pk=object_id)
        mk_names = Member.objects.values_list('name',flat=True)
        if user_input_type == 'agenda':
            try:
                agenda_id = int(request.POST.get('agenda'))
            except:
                return HttpResponseBadRequest()
            agenda = Agenda.objects.get(pk=agenda_id)
            reasoning = request.POST.get('reasoning','')
            usv = UserSuggestedVote.objects.filter(user = request.user,
                                agenda = agenda,
                                vote = vote)
            if usv:
                usv = usv[0]
                usv.reasoning = reasoning
                usv.sent_to_editor = False
                usv.save()
            else:
                usv = UserSuggestedVote(user = request.user,
                                agenda = agenda,
                                vote = vote,
                                reasoning = reasoning)
                usv.save()

        else: # adding an MK (either for or against)
            mk_name = difflib.get_close_matches(request.POST.get('mk_name'), mk_names)[0]
            mk = Member.objects.get(name=mk_name)
            stand = None
            if user_input_type == 'mk-for':
                stand = 'for'
            if user_input_type == 'mk-against':
                stand = 'against'
            if stand:
                va = VoteAction.objects.filter(member=mk, vote=vote)
                if va:
                    va = va[0]
                    va.type=stand
                    va.save()
                else:
                    va = VoteAction(member=mk, vote=vote, type=stand)
                    va.save()
                vote.update_vote_properties()

        return HttpResponseRedirect('.')


def tagged(request,tag):
    title = ugettext_lazy('Votes tagged %(tag)s') % {'tag': tag}
    try:
        return tagged_object_list(request, queryset_or_model = Vote, tag=tag, extra_context={'title':title})
    except Http404:
        return object_list(request, queryset=Vote.objects.none(), extra_context={'title':title})

def vote_auto_complete(request):
    if request.method != 'GET':
        raise Http404

    if not 'query' in request.GET:
        raise Http404

    options = Vote.objects.filter(title__icontains=request.GET['query'])[:30]

    data = []
    suggestions = []
    for i in options:
        data.append(i.id)
        suggestions.append(i.title)

    result = { 'query': request.GET['query'], 'suggestions':suggestions, 'data':data }

    return HttpResponse(json.dumps(result), mimetype='application/json')

def embed_bill_details(request, object_id):
    # TODO(shmichael): Only use the last stream item of each type, and if we find
    # contradictions, send to human operator for sanitizing.
    bill = get_object_or_404(Bill, pk=object_id)

    context = RequestContext (request,{'bill': bill})
    return render_to_response("laws/embed_bill_detail.html", context)
