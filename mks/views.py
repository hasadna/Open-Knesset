import urllib
from operator import attrgetter

from django.conf import settings
from django.db.models import Sum, Q
from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic import ListView, TemplateView
from django.core.cache import cache
from django.utils import simplejson as json
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from backlinks.pingback.server import default_server
from actstream import actor_stream
from actstream.models import Follow

from hashnav.detail import DetailView
from models import Member, Party
from utils import percentile
from laws.models import MemberVotingStatistics, Bill, VoteAction
from agendas.models import Agenda
from auxiliary.views import CsvView

from video.utils import get_videos_queryset
from datetime import date, timedelta

import logging
from auxiliary.views import GetMoreView


logger = logging.getLogger("open-knesset.mks")

class MemberListView(ListView):

    model = Member

    def get_template_names(self):
        info = self.request.GET.get('info','bills_pre')
        if info=='abc':
            return ['mks/member_list.html']
        elif info=='graph':
            return ['mks/member_graph.html']
        else:
            return ['mks/member_list_with_bars.html']

    def get_context_data(self, **kwargs):
        info = self.request.GET.get('info','bills_pre')
        if info not in ['abc','bills_proposed','bills_pre',
                        'bills_first','bills_approved','votes',
                        'presence','committees','graph']:
            raise Http404()
        original_context = super(MemberListView, self).get_context_data(**kwargs)
        qs = original_context['object_list'].filter(is_current=True)

        context = cache.get('object_list_by_%s' % info) or {}
        if context:
            original_context.update(context)
            return original_context
        context['past_mks'] = Member.objects.filter(is_current=False)

        context['friend_pages'] = [['.?info=abc',_('By ABC'), False],
                              ['.?info=bills_proposed',_('By number of bills proposed'), False],
                              ['.?info=bills_pre',_('By number of bills pre-approved'), False],
                              ['.?info=bills_first',_('By number of bills first-approved'), False],
                              ['.?info=bills_approved',_('By number of bills approved'), False],
                              ['.?info=votes', _('By number of votes per month'), False],
                              ['.?info=presence', _('By average weekly hours of presence'), False],
                              ['.?info=committees', _('By average monthly committee meetings'), False],
                              ['.?info=graph', _('Graphical view'), False]]
        if info=='abc':
            context['friend_pages'][0][2] = True
            context['title'] = _('Members')
        elif info=='bills_proposed':
            qs = qs.order_by('-bills_stats_proposed')\
                    .select_related('current_party')\
                    .extra(select={'extra':'bills_stats_proposed'})
            context['past_mks'] = context['past_mks'].order_by('-bills_stats_proposed')\
                                                     .select_related('current_party')\
                                                     .extra(select={'extra':'bills_stats_proposed'})
            context['friend_pages'][1][2] = True
            context['norm_factor'] = float(qs[0].bills_stats_proposed)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By number of bills proposed'))
            context['bill_stage'] = 'proposed'
        elif info=='bills_pre':
            qs = qs.order_by('-bills_stats_pre')\
                    .select_related('current_party')\
                    .extra(select={'extra':'bills_stats_pre'})
            context['past_mks'] = context['past_mks'].order_by('-bills_stats_pre')\
                                                     .select_related('current_party')\
                                                     .extra(select={'extra':'bills_stats_pre'})
            context['friend_pages'][2][2] = True
            context['norm_factor'] = float(qs[0].extra)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By number of bills pre-approved'))
            context['bill_stage'] = 'pre'
        elif info=='bills_first':
            qs = qs.order_by('-bills_stats_first')\
                    .select_related('current_party')\
                    .extra(select={'extra':'bills_stats_first'})
            context['past_mks'] = context['past_mks'].order_by('-bills_stats_first')\
                                                     .select_related('current_party')\
                                                     .extra(select={'extra':'bills_stats_first'})
            context['friend_pages'][3][2] = True
            context['norm_factor'] = float(qs[0].extra)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By number of bills first-approved'))
            context['bill_stage'] = 'first'
        elif info=='bills_approved':
            qs = qs.order_by('-bills_stats_approved')\
                    .select_related('current_party')\
                    .extra(select={'extra':'bills_stats_approved'})
            context['past_mks'] = context['past_mks'].order_by('-bills_stats_approved')\
                                                     .select_related('current_party')\
                                                     .extra(select={'extra':'bills_stats_approved'})
            context['friend_pages'][4][2] = True
            context['norm_factor'] = float(qs[0].extra)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By number of bills approved'))
            context['bill_stage'] = 'approved'
        elif info=='votes':
            qs = list(qs)
            vs = list(MemberVotingStatistics.objects.all())
            vs = dict(zip([x.member_id for x in vs],vs))
            for x in qs:
                x.extra = vs[x.id].average_votes_per_month()
            qs.sort(key=lambda x:x.extra, reverse=True)
            context['past_mks'] = list(context['past_mks'])
            for x in context['past_mks']:
                x.extra = x.voting_statistics.average_votes_per_month()
            context['past_mks'].sort(key=lambda x:x.extra, reverse=True)
            context['friend_pages'][5][2] = True
            context['norm_factor'] = float(qs[0].extra)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By number of votes per month'))
        elif info=='presence':
            qs = list(qs)
            for x in qs:
                x.extra = x.average_weekly_presence()
            qs.sort(key=lambda x:x.extra or 0, reverse=True)
            context['past_mks'] = list(context['past_mks'])
            for x in context['past_mks']:
                x.extra = x.average_weekly_presence()
            context['past_mks'].sort(key=lambda x:x.extra or 0, reverse=True)
            context['friend_pages'][6][2] = True
            context['norm_factor'] = float(qs[0].extra)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By average weekly hours of presence'))
        elif info=='committees':
            qs = list(qs)
            for x in qs:
                x.extra = x.committee_meetings_per_month()
            qs.sort(key=lambda x:x.extra or 0, reverse=True)
            context['past_mks'] = list(context['past_mks'])
            for x in context['past_mks']:
                x.extra = x.committee_meetings_per_month()
            context['past_mks'].sort(key=lambda x:x.extra or 0, reverse=True)
            context['friend_pages'][7][2] = True
            context['norm_factor'] = float(qs[0].extra)/50.0
            context['title'] = "%s %s" % (_('Members'), _('By average monthly committee meetings'))
        elif info=='graph':
            context['friend_pages'][8][2] = True
            context['title'] = "%s %s" % (_('Members'), _('Graphical view'))
        context['object_list']=qs
        cache.set('object_list_by_%s' % info, context, settings.LONG_CACHE_TIME)
        original_context.update(context)
        return original_context


class MemberCsvView(CsvView):
    model = Member
    filename = 'members.csv'
    list_display = (('name', _('Name')),
                    ('bills_stats_proposed', _('Bills Proposed')),
                    ('bills_stats_pre', _('Bills Pre-Approved')),
                    ('bills_stats_first', _('Bills First-Approved')),
                    ('bills_stats_approved', _('Bills Approved')),
                    ('average_votes_per_month', _('Average Votes per Month')),
                    ('average_weekly_presence', _('Average Weekly Presence')),
                    ('committee_meetings_per_month',
                     _('Committee Meetings per Month')))


class MemberDetailView(DetailView):

    queryset = Member.objects.select_related('current_party', 'voting_statistics')
    MEMBER_INITIAL_DATA = 2

    def calc_percentile(self,member,outdict,inprop,outvalprop,outpercentileprop):
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
        member_val = getattr(member,inprop) or 0

        avg = sum(x[inprop] or 0 for x in all_members) / member_count

        var = sum(((x[inprop] or 0) - avg) ** 2 for x in all_members) / member_count

        outdict[outvalprop] = member_val
        outdict[outpercentileprop] = percentile(avg,var,member_val) if var != 0 else 0

    def calc_bill_stats(self,member,bills_statistics,stattype):
        self.calc_percentile( member,
                              bills_statistics,
                              'bills_stats_%s' % stattype,
                              stattype,
                              '%s_percentile' % stattype)

    def get_context_data(self, **kwargs):
        context = super(MemberDetailView, self).get_context_data(**kwargs)
        member = context['object']

        if self.request.user.is_authenticated():
            p = self.request.user.get_profile()
            watched = member in p.members
            cached_context = None
        else:
            watched = False
            cached_context = cache.get('mk_%d' % member.id)

        if cached_context is None:
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
            self.calc_bill_stats(member,bills_statistics,'proposed')
            self.calc_bill_stats(member,bills_statistics,'pre')
            self.calc_bill_stats(member,bills_statistics,'first')
            self.calc_bill_stats(member,bills_statistics,'approved')

            if self.request.user.is_authenticated():
                agendas = Agenda.objects.get_selected_for_instance(member, user=self.request.user, top=3, bottom=3)
            else:
                agendas = Agenda.objects.get_selected_for_instance(member, user=None, top=3, bottom=3)
            agendas = agendas['top'] + agendas['bottom']
            for agenda in agendas:
                agenda.watched=False
                agenda.totals = agenda.get_mks_totals(member)
            if self.request.user.is_authenticated():
                watched_agendas = self.request.user.get_profile().agendas
                for watched_agenda in watched_agendas:
                    if watched_agenda in agendas:
                        agendas[agendas.index(watched_agenda)].watched = True
                    else:
                        watched_agenda.score = watched_agenda.member_score(member)
                        watched_agenda.watched = True
                        agendas.append(watched_agenda)
            agendas.sort(key=attrgetter('score'), reverse=True)

            factional_discipline = VoteAction.objects.select_related(
                'vote').filter(member = member, against_party=True)

            votes_against_own_bills = VoteAction.objects.select_related(
                'vote').filter(member=member, against_own_bill=True)

            general_discipline_params = { 'member' : member }
            is_coalition = member.current_party.is_coalition
            if is_coalition:
                general_discipline_params['against_coalition'] = True
            else:
                general_discipline_params['against_opposition'] = True
            general_discipline = VoteAction.objects.filter(
                **general_discipline_params).select_related('vote')

            about_videos=get_videos_queryset(member,group='about')[:1]
            if len(about_videos):
                about_video=about_videos[0]
                about_video_embed_link=about_video.embed_link
                about_video_image_link=about_video.image_link
            else:
                about_video_embed_link=''
                about_video_image_link=''

            related_videos=get_videos_queryset(member,group='related')
            related_videos=related_videos.filter(
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
            num_followers = Follow.objects.filter(object_id=member.pk, content_type=content_type).count()

            cached_context = {
                'watched_member': watched,
                'num_followers': num_followers,
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
            }

            if not self.request.user.is_authenticated():
                cache.set('mk_%d' % member.id, cached_context,
                          settings.LONG_CACHE_TIME)

        context.update(cached_context)
        return context

class PartyListView(ListView):

    model = Party

    def get_context_data(self, **kwargs):
        context = super(PartyListView, self).get_context_data(**kwargs)
        qs = context['object_list']
        info = self.request.GET.get('info','seats')
        context['coalition'] = qs.filter(is_coalition=True)
        context['opposition'] = qs.filter(is_coalition=False)
        context['friend_pages'] = [['.',_('By Number of seats'), False],
                              ['.?info=votes-per-seat', _('By votes per seat'), False],
                              ['.?info=discipline', _('By factional discipline'), False],
                              ['.?info=coalition-discipline', _('By coalition/opposition discipline'), False],
                              ['.?info=residence-centrality', _('By residence centrality'), False],
                              ['.?info=residence-economy', _('By residence economy'), False],
                              ['.?info=bills-proposed', _('By bills proposed'), False],
                              ['.?info=bills-pre', _('By bills passed pre vote'), False],
                              ['.?info=bills-first', _('By bills passed first vote'), False],
                              ['.?info=bills-approved', _('By bills approved'), False],
                              ['.?info=presence', _('By average weekly hours of presence'), False],
                              ['.?info=committees', _('By average monthly committee meetings'), False],
                              ]

        if info:
            if info=='seats':
                context['coalition']  =  context['coalition'].annotate(extra=Sum('number_of_seats')).order_by('-extra')
                context['opposition'] = context['opposition'].annotate(extra=Sum('number_of_seats')).order_by('-extra')
                context['friend_pages'][0][2] = True
                context['norm_factor'] = 1
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties'))
            if info=='votes-per-seat':
                m = 0
                for p in context['coalition']:
                    p.extra = p.voting_statistics.votes_per_seat()
                    if p.extra > m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = p.voting_statistics.votes_per_seat()
                    if p.extra > m:
                        m = p.extra
                context['friend_pages'][1][2] = True
                context['norm_factor'] = m/20
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties'))

            if info=='discipline':
                m = 100
                for p in context['coalition']:
                    p.extra = p.voting_statistics.discipline()
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = p.voting_statistics.discipline()
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][2][2] = True
                context['norm_factor'] = (100.0-m)/15
                context['baseline'] = m - 2
                context['title'] = "%s" % (_('Parties'))

            if info=='coalition-discipline':
                m = 100
                for p in context['coalition']:
                    p.extra = p.voting_statistics.coalition_discipline()
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = p.voting_statistics.coalition_discipline()
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][3][2] = True
                context['norm_factor'] = (100.0-m)/15
                context['baseline'] = m - 2
                context['title'] = "%s" % (_('Parties'))

            if info=='residence-centrality':
                m = 10
                for p in context['coalition']:
                    rc = [member.residence_centrality for member in p.members.all() if member.residence_centrality]
                    if rc:
                        p.extra = round(float(sum(rc))/len(rc),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    rc = [member.residence_centrality for member in p.members.all() if member.residence_centrality]
                    if rc:
                        p.extra = round(float(sum(rc))/len(rc),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][4][2] = True
                context['norm_factor'] = (10.0-m)/15
                context['baseline'] = m-1
                context['title'] = "%s" % (_('Parties by residence centrality'))

            if info=='residence-economy':
                m = 10
                for p in context['coalition']:
                    rc = [member.residence_economy for member in p.members.all() if member.residence_economy]
                    if rc:
                        p.extra = round(float(sum(rc))/len(rc),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    rc = [member.residence_economy for member in p.members.all() if member.residence_economy]
                    if rc:
                        p.extra = round(float(sum(rc))/len(rc),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][5][2] = True
                context['norm_factor'] = (10.0-m)/15
                context['baseline'] = m-1
                context['title'] = "%s" % (_('Parties by residence economy'))

            if info=='bills-proposed':
                m = 9999
                for p in context['coalition']:
                    p.extra = len(set(Bill.objects.filter(proposers__current_party=p).values_list('id',flat=True)))/p.number_of_seats
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = len(set(Bill.objects.filter(proposers__current_party=p).values_list('id',flat=True)))/p.number_of_seats
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][6][2] = True
                context['norm_factor'] = m/2
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties by number of bills proposed per seat'))

            if info=='bills-pre':
                m = 9999
                for p in context['coalition']:
                    p.extra = round(float(len(set(Bill.objects.filter(Q(proposers__current_party=p),Q(stage='2')|Q(stage='3')|Q(stage='4')|Q(stage='5')|Q(stage='6')).values_list('id',flat=True))))/p.number_of_seats,1)
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = round(float(len(set(Bill.objects.filter(Q(proposers__current_party=p),Q(stage='2')|Q(stage='3')|Q(stage='4')|Q(stage='5')|Q(stage='6')).values_list('id',flat=True))))/p.number_of_seats,1)
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][7][2] = True
                context['norm_factor'] = m/2
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties by number of bills passed pre vote per seat'))

            if info=='bills-first':
                m = 9999
                for p in context['coalition']:
                    p.extra = round(float(len(set(Bill.objects.filter(Q(proposers__current_party=p),Q(stage='4')|Q(stage='5')|Q(stage='6')).values_list('id',flat=True))))/p.number_of_seats,1)
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = round(float(len(set(Bill.objects.filter(Q(proposers__current_party=p),Q(stage='4')|Q(stage='5')|Q(stage='6')).values_list('id',flat=True))))/p.number_of_seats,1)
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][8][2] = True
                context['norm_factor'] = m/2
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties by number of bills passed first vote per seat'))

            if info=='bills-approved':
                m = 9999
                for p in context['coalition']:
                    p.extra = round(float(len(set(Bill.objects.filter(proposers__current_party=p,stage='6').values_list('id',flat=True))))/p.number_of_seats,1)
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    p.extra = round(float(len(set(Bill.objects.filter(proposers__current_party=p,stage='6').values_list('id',flat=True))))/p.number_of_seats,1)
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][9][2] = True
                context['norm_factor'] = m/2
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties by number of bills passed approved per seat'))

            if info=='presence':
                m = 9999
                for p in context['coalition']:
                    awp = [member.average_weekly_presence() for member in p.members.all() if member.average_weekly_presence()]
                    if awp:
                        p.extra = round(float(sum(awp))/len(awp),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    awp = [member.average_weekly_presence() for member in p.members.all() if member.average_weekly_presence()]
                    if awp:
                        p.extra = round(float(sum(awp))/len(awp),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][10][2] = True
                context['norm_factor'] = m/2
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties by average weekly hours of presence'))

            if info=='committees':
                m = 9999
                for p in context['coalition']:
                    cmpm = [member.committee_meetings_per_month() for member in p.members.all() if member.committee_meetings_per_month()]
                    if cmpm:
                        p.extra = round(float(sum(cmpm))/len(cmpm),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                for p in context['opposition']:
                    cmpm = [member.committee_meetings_per_month() for member in p.members.all() if member.committee_meetings_per_month()]
                    if cmpm:
                        p.extra = round(float(sum(cmpm))/len(cmpm),1)
                    else:
                        p.extra = 0
                    if p.extra < m:
                        m = p.extra
                context['friend_pages'][11][2] = True
                context['norm_factor'] = m/2
                context['baseline'] = 0
                context['title'] = "%s" % (_('Parties by monthly committee meetings'))

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

        if self.request.user.is_authenticated():
            agendas = Agenda.objects.get_selected_for_instance(party, user=self.request.user, top=3, bottom=3)
        else:
            agendas = Agenda.objects.get_selected_for_instance(party, user=None, top=3, bottom=3)
        agendas = agendas['top'] + agendas['bottom']
        for agenda in agendas:
            agenda.watched=False
        if self.request.user.is_authenticated():
            watched_agendas = self.request.user.get_profile().agendas
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
    if entry:
        return entry.backlinks_enabled
    return False

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
    """Get partially rendered member mmm documents content for AJAX calls to 'More'"""

    template_name = "mks/mmm_partials.html"
    paginate_by = 10

    def get_queryset(self):
        member = get_object_or_404(Member, pk=self.kwargs['pk'])
        return member.mmm_documents.order_by('-publication_date')


class PartiesMembersView(TemplateView):
    """Index page for parties and members."""

    template_name = 'mks/parties_members.html'

    def get_context_data(self, **kwargs):
        ctx = super(PartiesMembersView, self).get_context_data(**kwargs)

        ctx['coalition'] = Party.objects.filter(is_coalition=True).annotate(
            extra=Sum('number_of_seats')).order_by('-extra')
        ctx['opposition'] = Party.objects.filter(is_coalition=False).annotate(
            extra=Sum('number_of_seats')).order_by('-extra')
        ctx['past_members'] = Member.objects.filter(is_current=False)

        return ctx
