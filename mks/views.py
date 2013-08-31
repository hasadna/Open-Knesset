import urllib
from operator import attrgetter

from django.conf import settings
from django.db.models import Sum, Q
from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic import ListView, RedirectView
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from django.utils.decorators import method_decorator
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from backlinks.pingback.server import default_server
from actstream import actor_stream
from actstream.models import Follow
from hashnav.detail import DetailView
from models import Member, Party, Knesset
from utils import percentile
from laws.models import MemberVotingStatistics, Bill, VoteAction
from agendas.models import Agenda
from auxiliary.views import CsvView

from video.utils import get_videos_queryset
from datetime import date, timedelta

import logging
from auxiliary.views import GetMoreView
from auxiliary.serializers import PromiseAwareJSONEncoder


logger = logging.getLogger("open-knesset.mks")


class MemberRedirectView(RedirectView):
    "Redirect to first stats view"

    def get_redirect_url(self):
        return reverse('member-stats', kwargs={'stat_type': MemberListView.pages[0][0]})


class MemberListView(ListView):

    pages = (
        ('abc', _('By ABC')),
        ('bills_proposed', _('By number of bills proposed')),
        ('bills_pre', _('By number of bills pre-approved')),
        ('bills_first', _('By number of bills first-approved')),
        ('bills_approved', _('By number of bills approved')),
        ('votes', _('By number of votes per month')),
        ('presence', _('By average weekly hours of presence')),
        ('committees', _('By average monthly committee meetings')),
        ('graph', _('Graphical view'))
    )

    @staticmethod
    def get_queryset():
        return Member.current_knesset.all()

    @staticmethod
    def get_past_mks_and_objectlist(info, qs, context):
        if info == 'votes':
            vs = {x.member_id:x for x in MemberVotingStatistics.objects.all()}
            def get_select(take):
                def select(q):
                    y = list(q)
                    for x in y:
                        x.extra = take(x).average_votes_per_month
                    y.sort(key=lambda x: x.extra, reverse=True)
                    return y
                return select
            return (get_select(lambda x : x.voting_statistics),
                     get_select(lambda x : vs[x.id]))
        if info.startswith('bills'):
            t = context['bill_stage'] = info.split('_')[1]
            page = 'bills_stats_{}'.format(t)
            extra = {'extra': page}
            order_t = '-' + page
            def select(q):
                return list(q.order_by(order_t).select_related('current_party').extra(select=extra))
            return select, select
        if info in ['presence', 'committees']:
            attr = {'presence':'average_weekly_presence', 'committees':'committee_meetings_per_month'}[info]
            def select(q):
                y = list(q)
                for x in y:
                    x.extra = getattr(x, attr)
                y.sort(key=lambda x: x.extra or 0, reverse=True)
                return y
            return select, select
        
    def get_context_data(self, **kwargs):

        info = self.kwargs['stat_type']

        original_context = super(MemberListView, self).get_context_data(**kwargs)

        # Do we have it in the cache ? If so, update and return
        cache_query = 'object_list_by_{}'.format(info)
        context = cache.get(cache_query) or {}

        if not context:
            qs = original_context['object_list'].filter(is_current=True)
            context['friend_pages'] = self.pages
            context['stat_type'] = info
            context['title'] = dict(self.pages)[info]
            context['csv_path'] = 'api/v2/member?{}&format=csv&limit=0'.format(self.request.GET.urlencode())     
            context['past_mks'] = Member.current_knesset.filter(is_current=False)
    
            # We make sure qs are lists so that the template can get min/max
            if info not in ('graph', 'abc'):
                select_past, select_qs = self.get_past_mks_and_objectlist(info, qs, context)
                context['past_mks'], qs = select_past(context['past_mks']), select_qs(qs)
                context['max_current'] = qs[0].extra
                if context['past_mks']:
                    context['max_past'] = context['past_mks'][0].extra
                        
            context['object_list'] = qs
            cache.set(cache_query, context, settings.LONG_CACHE_TIME)
        original_context.update(context)
        return original_context


class MemberCsvView(CsvView):
    model = Member
    filename = 'members.csv'
    list_display = (
            ('name', _('Name')),
            ('bills_stats_proposed', _('Bills Proposed')),
            ('bills_stats_pre', _('Bills Pre-Approved')),
            ('bills_stats_first', _('Bills First-Approved')),
            ('bills_stats_approved', _('Bills Approved')),
            ('average_votes_per_month', _('Average Votes per Month')),
            ('average_weekly_presence', _('Average Weekly Presence')),
            ('committee_meetings_per_month',  _('Committee Meetings per Month')))


class MemberDetailView(DetailView):

    queryset = Member.objects.exclude(current_party__isnull=True)\
                             .select_related('current_party',
                                             'current_party__knesset',
                                             'voting_statistics')\
                             .prefetch_related('parties')

    MEMBER_INITIAL_DATA = 2

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(MemberDetailView, self).dispatch(*args, **kwargs)

    def calc_percentile(self, member, outdict, inprop, outvalprop, outpercentileprop):
        # store in instance var if needed, no need to access cache for each
        # call.
        #
        # If not found in the instance, than try to get from cache (and set if
        # not found), plus setting it as an instance var. Also removes default
        # ordering by name (we don't need it)
        all_members = getattr(self, '_all_members', None)

        if not all_members:
            all_members = cache.get('all_members', None)
            if not all_members:
                self._all_members = all_members = list(
                    Member.objects.filter(is_current=True).order_by().values())
                cache.set('all_members', all_members, settings.LONG_CACHE_TIME)

        member_count = float(len(all_members))
        pre = [x[inprop] for x in all_members if x[inprop]]
        avg = sum(pre) / member_count
        var = sum((x-avg) ** 2 for x in pre) / member_count

        member_val = getattr(member, inprop) or 0
        outdict[outvalprop] = member_val
        outdict[outpercentileprop] = var and percentile(avg, var, member_val)

    def calc_bill_stats(self,member, bills_statistics, stattype):
        self.calc_percentile( member,
                              bills_statistics,
                              'bills_stats_{}'.format(stattype),
                              stattype,
                              '{}_percentile'.format(stattype))

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data(**kwargs)
        member = context['object']
        user = self.request.user
        authenticated = user.is_authenticated()

        if authenticated:
            profile = user.get_profile()
            watched = member in profile.members
            cached_context = None
        else:
            watched = False
            cached_context = cache.get('mk_{}'.format(member.id))

        if not cached_context:
            presence = {}
            self.calc_percentile(member, presence,
                                 'average_weekly_presence_hours',
                                 'average_weekly_presence_hours',
                                 'average_weekly_presence_hours_percentile')
            self.calc_percentile(member, presence,
                                 'average_monthly_committee_presence',
                                 'average_monthly_committee_presence',
                                 'average_monthly_committee_presence_percentile')

            bills_statistics = {}
            for s in ('proposed', 'pre', 'first', 'approved'):
                self.calc_bill_stats(member,bills_statistics, s)
            
            agendas = Agenda.objects.get_selected_for_instance(member,
                                        user=user if authenticated else None, top=3, bottom=3)
            for agenda in agendas:
                agenda.watched = False
                agenda.totals = agenda.get_mks_totals(member)
            if authenticated:
                for watched_agenda in profile.agendas:
                    if watched_agenda in agendas:
                        agendas[agendas.index(watched_agenda)].watched = True
                    else:
                        watched_agenda.score = watched_agenda.member_score(member)
                        watched_agenda.watched = True
                        agendas.append(watched_agenda)
            agendas.sort(key=attrgetter('score'), reverse=True)

            factional_discipline = VoteAction.objects.select_related(
                'vote').filter(member=member, against_party=True)

            votes_against_own_bills = VoteAction.objects.select_related(
                'vote').filter(member=member, against_own_bill=True)

            general_discipline_params = { 'member' : member }
            side = 'against_coalition' if member.current_party.is_coalition else 'against_opposition'
            general_discipline_params[side] = True
            general_discipline = VoteAction.objects.filter(
                **general_discipline_params).select_related('vote')


            about_videos = get_videos_queryset(member,group='about')
            try:
                about_video_embed_link=about_videos[0].embed_link
                about_video_image_link=about_videos[0].image_link
            except IndexError: 
                about_video_embed_link=''
                about_video_image_link=''
                
            related_videos = get_videos_queryset(member,group='related').filter(
                                    Q(published__gt=date.today()-timedelta(days=30))
                                    | Q(sticky=True)
                                ).order_by('sticky').order_by('-published')[:5]

            actions = actor_stream(member)

            for a in actions:
                a.actor = member

            legislation_actions = actor_stream(member).filter(
                verb__in=('proposed', 'joined'))

            committee_actions = actor_stream(member).filter(verb='attended')
            mmm_documents = member.mmm_documents.order_by('-publication_date')
            content_type = ContentType.objects.get_for_model(Member)

            # since parties are prefetch_releated, will list and slice them
            previous_parties = list(member.parties.all())[1:]
            cached_context = {
                'watched_member': watched,
                'num_followers': Follow.objects.filter(object_id=member.pk, content_type=content_type).count(),
                'actions_more': actions.count() > self.MEMBER_INITIAL_DATA,
                'actions': actions[:self.MEMBER_INITIAL_DATA],
                'legislation_actions_more': legislation_actions.count() > self.MEMBER_INITIAL_DATA,
                'legislation_actions': legislation_actions[:self.MEMBER_INITIAL_DATA],
                'committee_actions_more': committee_actions.count() > self.MEMBER_INITIAL_DATA,
                'committee_actions': committee_actions[:self.MEMBER_INITIAL_DATA],
                'mmm_documents_more': mmm_documents.count() > self.MEMBER_INITIAL_DATA,
                'mmm_documents': mmm_documents[:self.MEMBER_INITIAL_DATA],
                'bills_statistics': bills_statistics,
                'agendas': agendas,
                'presence': presence,
                'current_knesset_start_date': date(2009, 2, 24),
                'factional_discipline': factional_discipline,
                'votes_against_own_bills': votes_against_own_bills,
                'general_discipline': general_discipline,
                'about_video_embed_link': about_video_embed_link,
                'about_video_image_link': about_video_image_link,
                'related_videos': related_videos,
                'num_related_videos': related_videos.count(),
                'INITIAL_DATA': self.MEMBER_INITIAL_DATA,
                'previous_parties': previous_parties,
            }

            if not authenticated:
                cache.set('mk_{}'.format(member.id), cached_context,
                          settings.LONG_CACHE_TIME)

        context.update(cached_context)
        return context


class PartyRedirectView(RedirectView):
    "Redirect to first stats view"

    def get_redirect_url(self):
        return reverse('party-stats', kwargs={'stat_type': PartyListView.pages[0][0]})


class PartyListView(ListView):

    model = Party

    def get_queryset(self):
        return self.model.objects.filter(
            knesset=Knesset.objects.current_knesset())

    pages = (
        ('seats', _('By Number of seats')),
        ('votes-per-seat', _('By votes per seat')),
        ('discipline', _('By factional discipline')),
        ('discipline-coalition', _('By coalition/opposition discipline')),
        ('residence-centrality', _('By residence centrality')),
        ('residence-economy', _('By residence economy')),
        ('bills-proposed', _('By bills proposed')),
        ('bills-pre', _('By bills passed pre vote')),
        ('bills-first', _('By bills passed first vote')),
        ('bills-approved', _('By bills approved')),
        ('presence', _('By average weekly hours of presence')),
        ('presence-committees', _('By average monthly committee meetings')),
    )
    
    def calculate_bills(self, info, qs):
        s2 = {'pre':       Q(stage__in={'2','3','4','5','6'}),
              'first':     Q(stage__in={'4','5','6'}),
              'approved':  Q(stage='6'),
              'proposed':  Q() }
        bills = Bill.objects.filter(s2[info.split('-')[1]]).prefetch_related(1)
        extras = []
        for p in qs:
            x = bills.filter(Q(proposers__current_party=p)).values_list('id',flat=True).distinct().count()
            if False:
                x = round(float(x)/p.number_of_seats, 1)
            extras.append(x)
        return (min(extras)/2, 0), False, extras
    
    def calculate_general_statistics(self, info, qs):
        attribute_select = {
        'votes-per-seat':       'votes_per_seat',
        'discipline':           'discipline',
        'discipline-coalition': 'coalition_discipline',
        'residence-centrality': 'residence_centrality',
        'residence-economy':    'residence_economy',
        'presence':             'average_weekly_presence',
        'presence-committees':  'committee_meetings_per_month'
        }
        attr = attribute_select[info]
        
        def callback1(qs):
            qs = list(qs)
            for p in qs:
                members = list(p.members.all())
                rc = filter(None, [getattr(x, attr) for x in members])
                yield len(rc) and round(float(sum(rc)) / len(rc), 1)
        def callback2(qs):
            qs = list(qs)
            for p in qs:
                yield getattr(p.voting_statistics, attr)
        
        statistics = {# norm,                     baseline,      choose, call |     group_by_all
        'votes':      ((lambda m : m/20,          lambda m : 0,   max,   callback2), True),
        'discipline': ((lambda m : (100.0-m)/15,  lambda m : m-2, min,   callback2), False),
        'residence':  ((lambda m : (10.0-m)/15,   lambda m : m-1, min,   callback1), True),
        'presence':   ((lambda m : m/2,           lambda m : 0,   min,   callback1), True)
        }
        
        (norm,  baseline, choose, call), group_by_all = statistics[info.split('-')[0]]
        extras = list(call(qs))
        m = choose(extras) 
        return (norm(m), baseline(m)), group_by_all, extras        

    def calculate_seats(self, info, qs):
        return (1, 0), True, [p.number_of_seats for p in qs]
        
    def get_context_data(self, **kwargs):
        context = super(PartyListView, self).get_context_data(**kwargs)
        info = context['stat_type'] = self.kwargs['stat_type']
        context['friend_pages'] = self.pages

        qs = context['object_list'].only('id', 'name', 'is_coalition', 'number_of_seats')
        if info=='seats': 
            func = self.calculate_seats
            qs = qs.order_by() 
        elif info.startswith('bills'):  func = self.calculate_bills
        else: func = self.calculate_general_statistics
        (context['norm_factor'], context['baseline']), group_by_all, extra_list = func(info, qs)
        qs = list(qs)
        
        context['coalition'] = [x for x in qs if x.is_coalition]
        context['opposition'] = [x for x in qs if not x.is_coalition]
        
        context['title'] = _(u'Parties by %s') % dict(self.pages)[info]
        
        fmt = u'{}<br><a href="{}">{}</a>' 
        extras = {p.id:value for p, value in zip(qs, extra_list)}
        #TODO: the sorting should actually happen on the client side.
        qs.sort(key= lambda x : extras[x.id], reverse=True)
        parties = list(enumerate(qs, 1))
        ticks = [(count + 0.5, fmt.format(extras[party.id], party.get_absolute_url(), party.name)) for count, party in parties]
        coalition_data = []
        opposition_data = []
        for count, party in parties:
            (coalition_data if party.is_coalition else opposition_data).append( (count, extras[party.id]) )
        
        graph_data = {
            'data': [
                {'label': _('Coalition'), 'data': coalition_data},
                {'label': _('Opposition'), 'data': opposition_data},
            ],
            'ticks': ticks
        }
        context['graph'] = json.dumps(graph_data, cls=PromiseAwareJSONEncoder)
        return context


class PartyCsvView(CsvView):
    model = Party
    filename = 'parties.csv'
    list_display = (('name', _('Name')),
                    ('number_of_members', _('Number of Members')),
                    ('number_of_seats', _('Number of Seats')),
                    ('get_affiliation', _('Affiliation')))

class PartyDetailView(DetailView):
    model = Party

    def get_context_data (self, **kwargs):
        context = super(PartyDetailView, self).get_context_data(**kwargs)
        party = context['object']
        context['maps_api_key'] = settings.GOOGLE_MAPS_API_KEY
        user = self.request.user
        authenticated_user = user if user.is_authenticated() else None
        
        agendas = Agenda.objects.get_selected_for_instance(party, user=authenticated_user, top=10, bottom=10)
        for agenda in agendas:
            agenda.watched=False
        if authenticated_user:
            watched_agendas = user.get_profile().agendas
            for watched_agenda in watched_agendas:
                if watched_agenda in agendas:
                    agendas[agendas.index(watched_agenda)].watched = True
                else:
                    watched_agenda.score = watched_agenda.party_score(party)
                    watched_agenda.watched = True
                    agendas.append(watched_agenda)
        agendas.sort(key=attrgetter('score'), reverse=True)

        context.update({'agendas':agendas})
        return context


def member_auto_complete(request):
    if request.method != 'GET':
        raise Http404

    if not 'query' in request.GET:
        raise Http404

    suggestions = map(lambda member: member.name, Member.objects.filter(name__icontains=request.GET['query'])[:30])

    result = { 'query': request.GET['query'], 'suggestions':suggestions }

    return HttpResponse(json.dumps(result), mimetype='application/json')


def object_by_name(request, objects):
    name = urllib.unquote(request.GET.get('q',''))
    results = objects.find(name)
    if results:
        return HttpResponseRedirect(results[0].get_absolute_url())
    raise Http404(_('No %(object_type)s found matching "%(name)s".' % {'object_type':objects.model.__name__,'name':name}))

def party_by_name(request):
    return object_by_name(request, Party.objects)

def member_by_name(request):
    return object_by_name(request, Member.objects)

def get_mk_entry(**kwargs):
    ''' in Django 1.3 the pony decided generic views get `pk` rather then
        an `object_id`, so we must be crafty and support either
    '''
    i = kwargs.get('pk', kwargs.get('object_id', False))
    return Member.objects.get(pk=i) if i else None

def mk_is_backlinkable(url, entry):
    return entry and entry.backlinks_enabled

mk_detail = default_server.register_view(MemberDetailView.as_view(), get_mk_entry, mk_is_backlinkable)

class MemeberMoreActionsView(GetMoreView):
    """Get partially rendered member actions content for AJAX calls to 'More'"""

    paginate_by = 10
    template_name = 'mks/action_partials.html'

    def get_queryset(self):
        member = get_object_or_404(Member, pk=self.kwargs['pk'])
        actions = actor_stream(member)
        return actions


class MemeberMoreLegislationView(MemeberMoreActionsView):
    """Get partially rendered member legislation actions content for AJAX calls to 'More'"""

    def get_queryset(self):
        actions = super(MemeberMoreLegislationView, self).get_queryset()
        return actions.filter(verb__in=('proposed', 'joined'))


class MemeberMoreCommitteeView(MemeberMoreActionsView):
    """Get partially rendered member committee actions content for AJAX calls to 'More'"""

    def get_queryset(self):
        actions = super(MemeberMoreCommitteeView, self).get_queryset()
        return actions.filter(verb='attended')


class MemeberMoreMMMView(MemeberMoreActionsView):
    """Get partially rendered member mmm documents content for AJAX calls to
    'More'"""

    template_name = "mks/mmm_partials.html"
    paginate_by = 10

    def get_queryset(self):
        member = get_object_or_404(Member, pk=self.kwargs['pk'])
        return member.mmm_documents.order_by('-publication_date')


class PartiesMembersRedirctView(RedirectView):
    "Redirect old url to listing of current knesset"

    def get_redirect_url(self):
        knesset = Knesset.objects.current_knesset()
        return reverse('parties-members-list', kwargs={'pk': knesset.number})


class PartiesMembersView(DetailView):
    """Index page for parties and members."""

    model = Knesset
    def get_context_data(self, **kwargs):
        ctx = super(PartiesMembersView, self).get_context_data(**kwargs)

        ctx['other_knessets'] = self.model.objects.exclude(
            number=self.object.number).order_by('-number')
        parties = list(Party.objects.filter(knesset=self.object).annotate(
                                        extra=Sum('number_of_seats')).order_by('-extra'))
        ctx['sides'] = ([x for x in parties if x.is_coalition], [x for x in parties if not x.is_coalition])
        ctx['past_members'] = Member.objects.filter(
            is_current=False, current_party__knesset=self.object)
        ctx['knesset_number'] =  self.object.number
        return ctx

class PartiesMembersPicturesView(PartiesMembersView):
    """Index page for parties and members."""
    template_name = 'mks/parties_members.html'
    
class PartiesMembersRawView(PartiesMembersView):
    """Index page for parties and members."""
    template_name = 'mks/parties_members_raw.html'
    