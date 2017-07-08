# -*- coding: utf-8 -*
import colorsys
import datetime
import difflib
import itertools
import json
import logging
import re

import waffle

import tagging
from actstream import action
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import (HttpResponse, HttpResponseRedirect, Http404,
                         HttpResponseForbidden)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView, ListView
from tagging.models import TaggedItem, Tag

import models
import ok_tag.tag_suggestions
from auxiliary.mixins import GetMoreView
from forms import EditTopicForm, LinksFormset
from hashnav import method_decorator as hashnav_method_decorator
from knesset.utils import clean_string_no_quotes
from laws.models import Bill, PrivateProposal
from links.models import Link
from lobbyists.models import Lobbyist
from mks.models import Member
from mks.utils import get_all_mk_names
from mmm.models import Document
from models import Committee, CommitteeMeeting, Topic
from ok_tag.views import BaseTagMemberListView
from knesset_data_django.committees import members_by_presence

logger = logging.getLogger("open-knesset.committees.views")


class CommitteeListView(ListView):
    context_object_name = 'committees'
    queryset = Committee.objects.exclude(type='plenum').exclude(hide=True)
    # paginate_by = 20
    INITIAL_TOPICS = 10

    def get_context_data(self, **kwargs):
        context = super(CommitteeListView, self).get_context_data(**kwargs)
        context['tags_cloud'] = Tag.objects.cloud_for_model(CommitteeMeeting)
        if waffle.flag_is_active(self.request, 'show_committee_topics'):
            context = self._add_topics_to_context(context)

        return context

    def _add_topics_to_context(self, context):
        context["topics"] = Topic.objects.summary()[:self.INITIAL_TOPICS]
        context["topics_more"] = \
            Topic.objects.summary().count() > self.INITIAL_TOPICS
        context["INITIAL_TOPICS"] = self.INITIAL_TOPICS
        return context


class TopicsMoreView(GetMoreView):
    """Get partially rendered member actions content for AJAX calls to 'More'"""

    paginate_by = 20
    template_name = 'committees/_topics_summary.html'

    def get_queryset(self):
        return Topic.objects.summary()


class CommitteeDetailView(DetailView):
    model = Committee
    queryset = Committee.objects.prefetch_related('members', 'chairpersons',
                                                  'replacements', 'events',
                                                  'meetings', ).all()
    view_cache_key = 'committee_detail_%d'
    SEE_ALL_THRESHOLD = 10

    def get_context_data(self, *args, **kwargs):
        context = super(CommitteeDetailView, self).get_context_data(**kwargs)
        cm = context['object']
        cm.sorted_mmm_documents = cm.mmm_documents.order_by(
            '-publication_date')[:self.SEE_ALL_THRESHOLD]

        cached_context = cache.get(self.view_cache_key % cm.id, {})
        if not cached_context:
            self._build_context_data(cached_context, cm)
            # cache.set('committee_detail_%d' % cm.id, cached_context,
            #           settings.LONG_CACHE_TIME)
        context.update(cached_context)

        return context

    def _build_context_data(self, cached_context, cm):
        cached_context['chairpersons'] = cm.chairpersons.all()
        cached_context['replacements'] = cm.replacements.all()

        if waffle.flag_is_active(self.request, 'show_member_presence'):
            cached_context['show_member_presence'] = True
            members = members_by_presence(cm, current_only=True)
        else:
            cached_context['show_member_presence'] = False
            members = cm.members_by_name(current_only=True)

        links = list(Link.objects.for_model(Member))
        links_by_member = {}
        for k, g in itertools.groupby(links, lambda x: x.object_pk):
            links_by_member[str(k)] = list(g)
        for member in members:
            member.cached_links = links_by_member.get(str(member.pk), [])
        cached_context['members'] = members
        recent_meetings, more_meetings_available = cm.recent_meetings(
            limit=self.SEE_ALL_THRESHOLD)
        cached_context['meetings_list'] = recent_meetings
        cached_context['more_meetings_available'] = more_meetings_available
        future_meetings, more_future_meetings_available = cm.future_meetings(
            limit=self.SEE_ALL_THRESHOLD)
        cached_context['future_meetings_list'] = future_meetings
        cached_context[
            'more_future_meetings_available'] = more_future_meetings_available
        cur_date = datetime.datetime.now()
        not_yet_published_meetings, more_unpublished_available = cm.protocol_not_yet_published_meetings(
            end_date=cur_date, limit=self.SEE_ALL_THRESHOLD)
        cached_context[
            'protocol_not_yet_published_list'] = not_yet_published_meetings
        cached_context[
            'more_unpublished_available'] = more_unpublished_available
        cached_context['annotations'] = cm.annotations.order_by('-timestamp')
        if waffle.flag_is_active(self.request, 'show_committee_topics'):
            cached_context['topics'] = cm.topic_set.summary()[:5]


class MeetingDetailView(DetailView):
    model = CommitteeMeeting

    _action_handlers = {
        'bill': '_handle_bill_update',
        'mk': '_handle_add_mk',
        'remove-mk': '_handle_remove_mk',
        'add-lobbyist': '_handle_add_lobbyist',
        'remove-lobbyist': '_handle_remove_lobbyist',
        'protocol': '_handle_add_protocol',

    }

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            # Double prefetch since prefetch does not work over filter
            queryset = queryset.filter(pk=pk).prefetch_related('parts',
                                                               'parts__speaker__mk',
                                                               'lobbyists_mentioned',
                                                               'mks_attended',
                                                               'mks_attended__current_party',
                                                               'committee__members',
                                                               'committee__chairpersons',
                                                               'committee__replacements')

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get_queryset(self):
        return super(MeetingDetailView, self).get_queryset().select_related(
            'committee')

    def get_context_data(self, *args, **kwargs):
        context = super(MeetingDetailView, self).get_context_data(**kwargs)
        cm = context['object']
        colors = {}
        speakers = cm.parts.order_by('speaker__mk').values_list('header',
                                                                'speaker__mk').distinct()
        n = speakers.count()
        for (i, (p, mk)) in enumerate(speakers):
            (r, g, b) = colorsys.hsv_to_rgb(float(i) / n, 0.5 if mk else 0.3,
                                            255)
            colors[p] = 'rgb(%i, %i, %i)' % (r, g, b)
        context['title'] = _('%(committee)s meeting on %(date)s') % {
            'committee': cm.committee.name,
            'date': cm.date_string}
        context['description'] = self._resolve_committee_meeting_description(
            cm)
        page = self.request.GET.get('page', None)
        if page:
            context['description'] += _(' page %(page)s') % {'page': page}
        context['colors'] = colors
        parts_lengths = {}
        for part in cm.parts.all():
            parts_lengths[part.id] = len(part.body)
        context['parts_lengths'] = json.dumps(parts_lengths)
        context['paginate_by'] = models.COMMITTEE_PROTOCOL_PAGINATE_BY

        if cm.committee.type != 'plenum' and \
                waffle.flag_is_active(self.request, 'show_member_presence'):
            # get meeting members with presence calculation
            meeting_members_ids = set(
                member.id for member in cm.mks_attended.all())
            members = members_by_presence(cm.committee, ids=meeting_members_ids)
            context['show_member_presence'] = True
        else:
            members = cm.mks_attended.order_by('name')
            context['show_member_presence'] = False

        links = list(Link.objects.for_model(Member))
        links_by_member = {}
        for k, g in itertools.groupby(links, lambda x: x.object_pk):
            links_by_member[str(k)] = list(g)
        for member in members:
            member.cached_links = links_by_member.get(str(member.pk), [])
        context['members'] = members

        meeting_text = [cm.topics] + [part.body for part in cm.parts.all()]
        context[
            'tag_suggestions'] = ok_tag.tag_suggestions.extract_suggested_tags(
            cm.tags,
            meeting_text)

        context['mentioned_lobbyists'] = cm.main_lobbyists_mentioned
        context[
            'mentioned_lobbyist_corporations'] = cm.main_lobbyist_corporations_mentioned

        return context

    def _resolve_committee_meeting_description(self, committee_meeting):
        description = _('%(committee)s meeting on %(date)s on topic %(topic)s') \
                      % {'committee': committee_meeting.committee.name,
                         'date': committee_meeting.date_string,
                         'topic': committee_meeting.topics}
        return clean_string_no_quotes(description)

    def _resolve_handler_by_user_input_type(self, user_input_type):
        handler = self._action_handlers.get(user_input_type)
        return getattr(self, handler)

    @hashnav_method_decorator(login_required)
    def post(self, request, **kwargs):
        cm = get_object_or_404(CommitteeMeeting, pk=kwargs['pk'])
        request = self.request
        user_input_type = request.POST.get('user_input_type')

        handler = self._resolve_handler_by_user_input_type(
            user_input_type=user_input_type)
        handler(cm, request)

        return HttpResponseRedirect(".")

    def _handle_add_protocol(self, cm, request):
        if not cm.protocol_text:  # don't override existing protocols
            cm.protocol_text = request.POST.get('protocol_text')
            cm.save()
            mks, mk_names = get_all_mk_names()
            cm.find_attending_members(mks, mk_names)
            cm.create_protocol_parts(mks=mks, mk_names=mk_names)


    def _handle_remove_lobbyist(self, cm, request):
        lobbyist_name = request.POST.get('lobbyist_name')
        if not lobbyist_name:
            raise Http404()
        try:
            lobbyist_to_remove = Lobbyist.objects.get(
                Q(Q(person__name=lobbyist_name) | Q(
                    person__aliases__name=lobbyist_name)))
            cm.lobbyists_mentioned.remove(lobbyist_to_remove)
        except Lobbyist.DoesNotExist:
            raise Http404()

    def _handle_add_lobbyist(self, cm, request):
        lobbyist_name = request.POST.get('lobbyist_name')
        if not lobbyist_name:
            raise Http404()
        try:
            lobbyist_to_add = Lobbyist.objects.get(
                Q(Q(person__name=lobbyist_name) | Q(
                    person__aliases__name=lobbyist_name)))
            cm.lobbyists_mentioned.add(lobbyist_to_add)
        except Lobbyist.DoesNotExist:
            raise Http404()

    def _handle_remove_mk(self, cm, request):
        mk_id = request.POST.get('mk_id')
        mk_name = request.POST.get('mk_name_to_remove')
        if not mk_id and mk_name:
            mk_names = Member.objects.values_list('name', flat=True)

            possible_matches = difflib.get_close_matches(mk_name, mk_names)
            if possible_matches:
                mk_name = possible_matches[0]
                mk = Member.objects.get(name=mk_name)
        elif mk_id:
            mk = Member.objects.get(id=mk_id)
        else:
            raise Http404()
        cm.mks_attended.remove(mk)
        cm.save()  # just to signal, so the attended Action gets created.
        action.send(request.user,
                    verb='removed-mk-to-cm',
                    description=cm,
                    target=mk,
                    timestamp=datetime.datetime.now())

    def _handle_add_mk(self, cm, request):
        mk_id = request.POST.get('mk_id')
        mk_name = request.POST.get('mk_name')
        if not mk_id and mk_name:
            mk_names = Member.objects.values_list('name', flat=True)
            possible_matches = difflib.get_close_matches(mk_name, mk_names)
            if possible_matches:
                mk_name = possible_matches[0]
                mk = Member.objects.get(name=mk_name)
            else:
                raise Http404()

        elif mk_id:
            mk = Member.objects.get(id=mk_id)
        else:
            raise Http404()
        cm.mks_attended.add(mk)
        cm.save()  # just to signal, so the attended Action gets created.
        action.send(request.user,
                    verb='added-mk-to-cm',
                    description=cm,
                    target=mk,
                    timestamp=datetime.datetime.now())

    def _handle_bill_update(self, cm, request):
        bill_id = request.POST.get('bill_id')
        if not bill_id:
            raise Http404()
        if bill_id.isdigit():
            bill = get_object_or_404(Bill, pk=bill_id)
        else:  # not a number, maybe its p/1234
            m = re.findall('\d+', bill_id)
            if len(m) != 1:
                raise ValueError(
                    "didn't find exactly 1 number in bill_id=%s" % bill_id)
            pp = PrivateProposal.objects.get(proposal_id=m[0])
            bill = pp.bill
        if bill.stage in ['1', '2', '-2',
                          '3']:  # this bill is in early stage, so cm must be one of the first meetings
            bill.first_committee_meetings.add(cm)
        else:  # this bill is in later stages
            v = bill.first_vote  # look for first vote
            if v and v.time.date() < cm.date:  # and check if the cm is after it,
                bill.second_committee_meetings.add(
                    cm)  # if so, this is a second committee meeting
            else:  # otherwise, assume its first cms.
                bill.first_committee_meetings.add(cm)
        bill.update_stage()
        action.send(request.user, verb='added-bill-to-cm',
                    description=cm,
                    target=bill,
                    timestamp=datetime.datetime.now())


_('added-bill-to-cm')
_('added-mk-to-cm')
_('removed-mk-from-cm')


class TopicListView(ListView):
    model = Topic
    context_object_name = 'topics'

    def get_queryset(self):
        qs = Topic.objects.get_public()
        if "committee_id" in self.kwargs:
            qs = qs.filter(committees__id=self.kwargs["committee_id"])
        return qs

    def get_context_data(self, **kwargs):
        context = super(TopicListView, self).get_context_data(**kwargs)
        committee_id = self.kwargs.get("committee_id", False)
        context["committee"] = committee_id and Committee.objects.get(
            pk=committee_id)
        return context


class TopicDetailView(DetailView):
    model = Topic
    context_object_name = 'topic'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(TopicDetailView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TopicDetailView, self).get_context_data(**kwargs)
        topic = context['object']
        if self.request.user.is_authenticated():
            p = self.request.user.profiles.get()
            watched = topic in p.topics
        else:
            watched = False
        context['watched_object'] = watched
        return context


@login_required
def edit_topic(request, committee_id, topic_id=None):
    if request.method == 'POST':
        if topic_id:
            t = Topic.objects.get(pk=topic_id)
            if not t.can_edit(request.user):
                return HttpResponseForbidden()
        else:
            t = None
        edit_form = EditTopicForm(data=request.POST, instance=t)
        links_formset = LinksFormset(request.POST)
        if edit_form.is_valid() and links_formset.is_valid():
            topic = edit_form.save(commit=False)
            if topic_id:
                topic.id = topic_id
            else:  # new topic
                topic.creator = request.user
            topic.save()
            edit_form.save_m2m()
            links = links_formset.save(commit=False)
            ct = ContentType.objects.get_for_model(topic)
            for link in links:
                link.content_type = ct
                link.object_pk = topic.id
                link.save()

            messages.add_message(request, messages.INFO,
                                 'Topic has been updated')
            return HttpResponseRedirect(
                reverse('topic-detail', args=[topic.id]))

    if request.method == 'GET':
        if topic_id:  # editing existing topic
            t = Topic.objects.get(pk=topic_id)
            if not t.can_edit(request.user):
                return HttpResponseForbidden()
            edit_form = EditTopicForm(instance=t)
            ct = ContentType.objects.get_for_model(t)
            links_formset = LinksFormset(queryset=Link.objects.filter(
                content_type=ct, object_pk=t.id))
        else:  # create new topic for given committee
            c = Committee.objects.get(pk=committee_id)
            edit_form = EditTopicForm(initial={'committees': [c]})
            links_formset = LinksFormset(queryset=Link.objects.none())
    return render_to_response('committees/edit_topic.html',
                              context_instance=RequestContext(request,
                                                              {
                                                                  'edit_form': edit_form,
                                                                  'links_formset': links_formset,
                                                              }))


@login_required
def delete_topic(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    if topic.can_edit(request.user):
        # Delete on POST
        if request.method == 'POST':
            topic.status = models.TOPIC_DELETED
            topic.save()
            return HttpResponseRedirect(reverse('committee-detail',
                                                args=[topic.committees.all()[
                                                          0].id]))

        # Render a form on GET
        else:
            return render_to_response('committees/delete_topic.html',
                                      {'topic': topic},
                                      RequestContext(request)
                                      )
    else:
        raise Http404


class MeetingsListView(ListView):
    allow_empty = False
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super(MeetingsListView, self).get_context_data(**kwargs)
        committee_id = self.kwargs.get('committee_id')
        if committee_id:
            items = context['object_list']
            committee = items[0].committee

            if committee.type == 'plenum':
                committee_name = _('Knesset Plenum')
            else:
                committee_name = committee.name
            context['title'] = _('All meetings by %(committee)s') % {
                'committee': committee_name}
            context['committee'] = committee
        else:
            context['title'] = _('Parliamentary committees meetings')
        context['committee_id'] = committee_id

        context['none'] = _('No %(object_type)s found') % {
            'object_type': CommitteeMeeting._meta.verbose_name_plural}

        return context

    def get_queryset(self):
        c_id = self.kwargs.get('committee_id', None)
        qs = CommitteeMeeting.objects.filter_and_order(
            **dict(self.request.GET))
        if c_id:
            qs = qs.filter(committee__id=c_id)
        return qs


class UnpublishedProtocolslistView(ListView):
    allow_empty = False
    paginate_by = 20
    template_name = 'committees/committee_full_events_list.html'

    def get_context_data(self, *args, **kwargs):
        context = super(UnpublishedProtocolslistView, self).get_context_data(
            **kwargs)
        committee_id = self.kwargs.get('committee_id')
        if committee_id:
            # items = context['object_list']
            committee = Committee.objects.get(pk=committee_id)

            if committee.type == 'plenum':
                committee_name = _('Knesset Plenum')
            else:
                committee_name = committee.name
            context['title'] = _(
                'All unpublished protocols by %(committee)s') % {
                                   'committee': committee_name}
            context['committee'] = committee
        else:
            raise Http404('missing committee_id')

        context['committee_id'] = committee_id

        context['none'] = _('No %(object_type)s found') % {
            'object_type': CommitteeMeeting._meta.verbose_name_plural}

        return context

    def get_queryset(self):
        committee_id = self.kwargs.get('committee_id')
        committee = Committee.objects.get(pk=committee_id)
        end_date = datetime.datetime.now()
        qs = committee.protocol_not_yet_published_meetings(end_date=end_date,
                                                           do_limit=False)
        return qs


class FutureMeetingslistView(ListView):
    allow_empty = False
    paginate_by = 20
    template_name = 'committees/committee_full_events_list.html'

    def get_context_data(self, *args, **kwargs):
        context = super(FutureMeetingslistView, self).get_context_data(
            **kwargs)
        committee_id = self.kwargs.get('committee_id')
        if committee_id:
            committee = Committee.objects.get(pk=committee_id)

            if committee.type == 'plenum':
                committee_name = _('Knesset Plenum')
            else:
                committee_name = committee.name
            context['title'] = _('All future meetings by %(committee)s') % {
                'committee': committee_name}
            context['committee'] = committee
        else:
            raise Http404('missing committee_id')

        context['committee_id'] = committee_id

        context['none'] = _('No %(object_type)s found') % {
            'object_type': CommitteeMeeting._meta.verbose_name_plural}

        return context

    def get_queryset(self):
        committee_id = self.kwargs.get('committee_id')
        committee = Committee.objects.get(pk=committee_id)
        qs = committee.future_meetings(do_limit=False)
        return qs


def parse_date(date_string):
    return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()


def meeting_list_by_date(request, *args, **kwargs):
    committee_id = kwargs.get('committee_id')
    date_string = kwargs.get('date')
    try:
        date = parse_date(date_string)
    except:
        raise Http404()
    context = {}
    if committee_id:
        committee = Committee.objects.filter(pk=committee_id)[:1]
        if not committee:  # someone tried this with a non-existent committee
            raise Http404()
        else:
            committee = committee[0]
            context['committee'] = committee
            qs = CommitteeMeeting.objects.filter(committee_id=committee_id)
            context['title'] = _(
                'Meetings by %(committee)s on date %(date)s') % {
                                   'committee': committee, 'date': date}
            context['committee_id'] = committee_id
    else:
        context['title'] = _(
            'Parliamentary committees meetings on date %(date)s') % {
                               'date': date}
        qs = CommitteeMeeting.objects.all()
    qs = qs.filter(date=date)

    context['object_list'] = qs
    context['none'] = _('No %(object_type)s found') % {
        'object_type': CommitteeMeeting._meta.verbose_name_plural}

    return render_to_response("committees/committeemeeting_list.html",
                              context,
                              context_instance=RequestContext(request))


class MeetingTagListView(BaseTagMemberListView):
    template_name = 'committees/committeemeeting_list_by_tag.html'
    url_to_reverse = 'committeemeeting-tag'

    def get_queryset(self):
        return TaggedItem.objects.get_by_model(CommitteeMeeting,
                                               self.tag_instance)

    def get_mks_cloud(self):
        mks = [cm.mks_attended.all() for cm in
               TaggedItem.objects.get_by_model(
                   CommitteeMeeting, self.tag_instance)]
        d = {}
        for mk in mks:
            for p in mk:
                d[p] = d.get(p, 0) + 1
        # now d is a dict: MK -> number of meetings in this tag
        mks = d.keys()
        for mk in mks:
            mk.count = d[mk]
        return tagging.utils.calculate_cloud(mks)

    def get_context_data(self, *args, **kwargs):
        context = super(MeetingTagListView, self).get_context_data(*args,
                                                                   **kwargs)

        context['title'] = ugettext_lazy(
            'Committee Meetings tagged %(tag)s') % {
                               'tag': self.tag_instance.name}

        context['members'] = self.get_mks_cloud()
        return context


# TODO: This has be replaced by the class based view above for Django 1.5.
# Remove once working
#
# def meeting_tag(request, tag):
#    tag_instance = get_tag(tag)
#    if tag_instance is None:
#        raise Http404(_('No Tag found matching "%s".') % tag)
#
#    extra_context = {'tag':tag_instance}
#    extra_context['tag_url'] = reverse('committeemeeting-tag',args=[tag_instance])
#    extra_context['title'] = ugettext_lazy('Committee Meetings tagged %(tag)s') % {'tag': tag}
#    qs = CommitteeMeeting
#    queryset = TaggedItem.objects.get_by_model(qs, tag_instance)
#    mks = [cm.mks_attended.all() for cm in
#           TaggedItem.objects.get_by_model(CommitteeMeeting, tag_instance)]
#    d = {}
#    for mk in mks:
#        for p in mk:
#            d[p] = d.get(p,0)+1
#    # now d is a dict: MK -> number of meetings in this tag
#    mks = d.keys()
#    for mk in mks:
#        mk.count = d[mk]
#    mks = tagging.utils.calculate_cloud(mks)
#    extra_context['members'] = mks
#    return generic.list_detail.object_list(request, queryset,
#        template_name='committees/committeemeeting_list_by_tag.html', extra_context=extra_context)

def delete_topic_rating(request, object_id):
    if request.method == 'POST':
        topic = get_object_or_404(Topic, pk=object_id)
        topic.rating.delete(request.user, request.META['REMOTE_ADDR'])
        return HttpResponse('Vote deleted.')


class CommitteeMMMDocuments(ListView):
    paginate_by = 20
    allow_empty = True
    template_name = 'committees/committee_mmm_documents.html'

    def get_queryset(self):
        self.c_id = self.kwargs.get('committee_id')
        date = self.kwargs.get('date', None)
        if date:
            try:
                date = parse_date(date)
                documents = Document.objects.filter(
                    req_committee__id=self.c_id,
                    publication_date=date).order_by(
                    '-publication_date')
            except:
                raise
        else:
            documents = Document.objects.filter(
                req_committee__id=self.c_id).order_by(
                '-publication_date')
        return documents

    def get_context_data(self, **kwargs):
        context = super(CommitteeMMMDocuments, self).get_context_data(**kwargs)
        committee = Committee.objects.get(id=self.c_id)
        context['committee'] = committee.name
        context['committee_id'] = self.c_id
        context['committee_url'] = committee.get_absolute_url()
        return context
