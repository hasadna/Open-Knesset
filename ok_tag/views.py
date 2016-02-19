import tagging
from actstream import action
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden, HttpResponse, HttpResponseNotAllowed, HttpResponseBadRequest, \
    HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from tagging.models import TaggedItem, Tag
from tagging.utils import get_tag

from auxiliary.forms import TagSuggestionForm
from auxiliary.mixins import GetMoreView
from auxiliary.models import TagSuggestion, TagSynonym
from auxiliary.views import logger
from committees.models import CommitteeMeeting
from knesset.utils import notify_responsible_adult
from laws.models import Vote, Bill
from mks.models import Member, Knesset
from ok_tag.knesset_paginator import SelectorPaginator


class BaseTagMemberListView(ListView):
    """Generic helper for common tagged objects and optionally member
    operations. Should be inherited by others"""

    url_to_reverse = None  # override in inherited for reversing tag_url

    # in context

    @property
    def tag_instance(self):
        if not hasattr(self, '_tag_instance'):
            tag = self.kwargs['tag']
            self._tag_instance = get_tag(tag)

            if self._tag_instance is None:
                raise Http404(_('No Tag found matching "%s".') % tag)

        return self._tag_instance

    @property
    def member(self):
        if not hasattr(self, '_member'):
            member_id = self.request.GET.get('member', False)

            if member_id:
                try:
                    member_id = int(member_id)
                except ValueError:
                    raise Http404(
                        _('No Member found matching "%s".') % member_id)

                self._member = get_object_or_404(Member, pk=member_id)
            else:
                self._member = None

        return self._member

    def get_context_data(self, *args, **kwargs):
        context = super(BaseTagMemberListView, self).get_context_data(
            *args, **kwargs)

        context['tag'] = self.tag_instance
        context['tag_url'] = reverse(self.url_to_reverse,
                                     args=[self.tag_instance])

        if self.member:
            context['member'] = self.member
            context['member_url'] = reverse(
                'member-detail', args=[self.member.pk])

        user = self.request.user
        if user.is_authenticated():
            context['watched_members'] = user.get_profile().members
        else:
            context['watched_members'] = False

        return context


@require_http_methods(['POST'])
def suggest_tag_post(request):
    "Post a tag suggestion form"
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    form = TagSuggestionForm(request.POST)
    if form.is_valid():
        content_type = ContentType.objects.get_by_natural_key(form.cleaned_data['app_label'],
                                                              form.cleaned_data['object_type'])
        object = content_type.get_object_for_this_type(pk=form.cleaned_data['object_id'])
        ts = TagSuggestion(
            name=form.cleaned_data['name'],
            suggested_by=request.user,
            object=object
        )
        ts.save()

    return form.get_response()


def _add_tag_to_object(user, app, object_type, object_id, tag):
    ctype = ContentType.objects.get_by_natural_key(app, object_type)
    (ti, created) = TaggedItem._default_manager.get_or_create(
        tag=tag,
        content_type=ctype,
        object_id=object_id)
    action.send(user, verb='tagged', target=ti, description='%s' % (tag.name))
    url = reverse('tag-detail', kwargs={'slug': tag.name})
    return HttpResponse("{'id':%d, 'name':'%s', 'url':'%s'}" % (tag.id,
                                                                tag.name,
                                                                url))


@login_required
def add_tag_to_object(request, app, object_type, object_id):
    """add a POSTed tag_id to object_type object_id by the current user"""
    if request.method == 'POST' and 'tag_id' in request.POST:  # If the form has been submitted...
        tag = get_object_or_404(Tag, pk=request.POST['tag_id'])
        return _add_tag_to_object(request.user, app, object_type, object_id, tag)

    return HttpResponseNotAllowed(['POST'])


@login_required
def remove_tag_from_object(request, app, object_type, object_id):
    """remove a POSTed tag_id from object_type object_id"""
    ctype = ContentType.objects.get_by_natural_key(app, object_type)
    if request.method == 'POST' and 'tag_id' in request.POST:  # If the form has been submitted...
        tag = get_object_or_404(Tag, pk=request.POST['tag_id'])
        ti = TaggedItem._default_manager.filter(tag=tag, content_type=ctype, object_id=object_id)
        if len(ti) == 1:
            logger.debug('user %s is deleting tagged item %d' % (request.user.username, ti[0].id))
            ti[0].delete()
            action.send(request.user, verb='removed-tag', target=ti[0], description='%s' % (tag.name))
        else:
            logger.debug('user %s tried removing tag %d from object, but failed, because len(tagged_items)!=1' % (
                request.user.username, tag.id))
    return HttpResponse("{'id':%d,'name':'%s'}" % (tag.id, tag.name))


@permission_required('tagging.add_tag')
def create_tag_and_add_to_item(request, app, object_type, object_id):
    """adds tag with name=request.POST['tag'] to the tag list, and tags the given object with it
    ****
    Currently not used anywhere, sine we don't want to allow users to add
    more tags for now.
    """
    if request.method == 'POST' and 'tag' in request.POST:
        tag = request.POST['tag'].strip()
        msg = "user %s is creating tag %s on object_type %s and object_id %s".encode('utf8') % (
            request.user.username, tag, object_type, object_id)
        logger.info(msg)
        notify_responsible_adult(msg)
        if len(tag) < 3:
            return HttpResponseBadRequest()
        tags = Tag.objects.filter(name=tag)
        if not tags:
            try:
                tag = Tag.objects.create(name=tag)
            except Exception:
                logger.warn("can't create tag %s" % tag)
                return HttpResponseBadRequest()
        if len(tags) == 1:
            tag = tags[0]
        if len(tags) > 1:
            logger.warn("More than 1 tag: %s" % tag)
            return HttpResponseBadRequest()
        return _add_tag_to_object(request.user, app, object_type, object_id, tag)
    else:
        return HttpResponseNotAllowed(['POST'])


@permission_required('tagging.add_tag')
def add_tag_synonym(request, parent_tag_id, synonym_tag_id):
    parent_tag = Tag.objects.get(pk=parent_tag_id)
    synonym_tag = Tag.objects.get(pk=synonym_tag_id)
    assert parent_tag.synonym_synonym_tag.count() == 0
    assert synonym_tag != parent_tag
    TagSynonym.objects.create(tag_id=parent_tag_id, synonym_tag_id=synonym_tag_id)
    return HttpResponse('ok')


def calculate_cloud_from_models(*args):
    from tagging.models import Tag
    cloud = Tag._default_manager.cloud_for_model(args[0])
    for model in args[1:]:
        for tag in Tag._default_manager.cloud_for_model(model):
            if tag in cloud:
                cloud[cloud.index(tag)].count += tag.count
            else:
                cloud.append(tag)
    return tagging.utils.calculate_cloud(cloud)


class TagList(ListView):
    """Tags index view"""

    model = Tag
    template_name = 'auxiliary/tag_list.html'

    def get_queryset(self):
        return Tag.objects.all()

    def get_context_data(self, **kwargs):
        context = super(TagList, self).get_context_data(**kwargs)
        tags_cloud = cache.get('tags_cloud', None)
        if not tags_cloud:
            tags_cloud = calculate_cloud_from_models(Vote, Bill, CommitteeMeeting)
            tags_cloud.sort(key=lambda x: x.name)
            cache.set('tags_cloud', tags_cloud, settings.LONG_CACHE_TIME)
        context['tags_cloud'] = tags_cloud
        return context


class knessetAwareMixin:
    def get_knesset(self):

        needed_knesset_id = self.request.GET.get('knesset')
        if needed_knesset_id:
            try:
                knesset = Knesset.objects.filter(number=needed_knesset_id)[0]
            except IndexError as e:
                raise Http404('Invalid knesset number (Knesset=%s)' % (needed_knesset_id,))
        else:

            knesset = Knesset.objects.current_knesset()
        return knesset


class TagDetail(DetailView, knessetAwareMixin):
    """Tags index view"""

    model = Tag

    template_name = 'auxiliary/tag_detail.html'
    slug_field = 'name'

    def create_tag_cloud(self, tag, limit=30, bills=None, votes=None, cms=None):
        """
        Create tag could for tag <tag>. Returns only the <limit> most tagged members
        """

        try:
            mk_limit = int(self.request.GET.get('limit', limit))
        except ValueError:
            mk_limit = limit
        if bills is None:
            bills = TaggedItem.objects.get_by_model(Bill, tag) \
                .prefetch_related('proposers')
        if votes is None:
            votes = TaggedItem.objects.get_by_model(Vote, tag) \
                .prefetch_related('votes')
        if cms is None:
            cms = TaggedItem.objects.get_by_model(CommitteeMeeting, tag) \
                .prefetch_related('mks_attended')
        mk_taggeds = [(b.proposers.all(), b.stage_date) for b in bills]
        mk_taggeds += [(v.votes.all(), v.time.date()) for v in votes]
        mk_taggeds += [(cm.mks_attended.all(), cm.date) for cm in cms]
        current_k_start = Knesset.objects.current_knesset().start_date
        d = {}
        d_previous = {}
        for tagged, date in mk_taggeds:
            if date and (date > current_k_start):
                for p in tagged:
                    d[p] = d.get(p, 0) + 1
            else:  # not current knesset
                for p in tagged:
                    d_previous[p] = d.get(p, 0) + 1
        # now d is a dict: MK -> number of tagged in Bill, Vote and
        # CommitteeMeeting in this tag, in the current knesset
        # d_previous is similar, but for all non current knesset data
        mks = dict(sorted(d.items(), lambda x, y: cmp(y[1], x[1]))[:mk_limit])
        # Now only the most tagged are in the dict (up to the limit param)
        for mk in mks:
            mk.count = d[mk]
        mks = tagging.utils.calculate_cloud(mks)

        mks_previous = dict(sorted(d_previous.items(),
                                   lambda x, y: cmp(y[1], x[1]))[:mk_limit])
        for mk in mks_previous:
            mk.count = d_previous[mk]
        mks_previous = tagging.utils.calculate_cloud(mks_previous)
        return mks, mks_previous

    def get(self, *args, **kwargs):
        tag = self.get_object()
        ts = TagSynonym.objects.filter(synonym_tag=tag)
        if len(ts) > 0:
            proper = ts[0].tag
            url = reverse('tag-detail', kwargs={'slug': proper.name})
            return HttpResponsePermanentRedirect(url)
        else:
            return super(TagDetail, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TagDetail, self).get_context_data(**kwargs)
        knesset = self.get_knesset()
        context['knesset_id'] = knesset
        tag = context['object']

        cms_date_filter, proposal_date_filter, vote_date_filter = self._resolve_date_filters(knesset)

        votes = Vote.objects.filter(vote_date_filter)
        cms = CommitteeMeeting.committees_only.filter(cms_date_filter)

        context['bills'] = self._get_relevant_bills_by_tag(cms, proposal_date_filter, tag, votes)

        context['votes'] = self._get_relevant_votes_by_tag(tag, votes)
        cms, more_committee_meetings = self._get_relevant_committee_meetings_by_tag(cms, tag)
        context['cms'] = cms
        context['more_committee_meetings'] = more_committee_meetings

        (context['members'],
         context['past_members']) = self.create_tag_cloud(tag)

        context['paginator'] = paginator = SelectorPaginator(Knesset.objects.values_list('number', flat=True))
        context['page_obj'] = paginator.page(knesset.number)
        context['request'] = None

        return context

    def _get_relevant_committee_meetings_by_tag(self, cms, tag):
        cm_ct = ContentType.objects.get_for_model(CommitteeMeeting)
        cm_ids = TaggedItem.objects.filter(
            tag=tag, content_type=cm_ct).values_list('object_id', flat=True)
        cms = cms.filter(id__in=cm_ids).order_by('-date')
        number_of_tagged_items_in_first_batch = 5
        return cms[:number_of_tagged_items_in_first_batch], cms.count() > number_of_tagged_items_in_first_batch
        # return cms[:1], cms.count() > 1

    def _get_relevant_votes_by_tag(self, tag, votes):
        votes_ct = ContentType.objects.get_for_model(Vote)
        vote_ids = TaggedItem.objects.filter(
            tag=tag, content_type=votes_ct).values_list('object_id', flat=True)
        votes = votes.filter(id__in=vote_ids).order_by('-time')

        return votes

    def _get_relevant_bills_by_tag(self, cms, proposal_date_filter, tag, votes):
        knesset_bills = Bill.objects.filter(
            Q(pre_votes__in=votes)
            | Q(first_committee_meetings__in=cms)
            | Q(first_vote__in=votes)
            | Q(second_committee_meetings__in=cms)
            | Q(approval_vote__in=votes)
            | proposal_date_filter
        ).distinct()
        bills_ct = ContentType.objects.get_for_model(Bill)
        bill_ids = TaggedItem.objects.filter(
            tag=tag,
            content_type=bills_ct).values_list('object_id', flat=True)
        bills = knesset_bills.filter(id__in=bill_ids)
        return bills

    def _resolve_date_filters(self, knesset):
        knesset_end_date = knesset.end_date
        knesset_start_date = knesset.start_date
        if knesset_end_date is not None:
            cms_date_filter = Q(date__gte=knesset_start_date, date__lte=knesset_end_date)
            vote_date_filter = Q(time__gte=knesset_start_date, time__lte=knesset_end_date)
            proposal_date_filter = Q(proposals__date__gte=knesset_start_date, proposals__date__lte=knesset_end_date)
        else:
            cms_date_filter = Q(date__gte=knesset_start_date)
            vote_date_filter = Q(time__gte=knesset_start_date)
            proposal_date_filter = Q(proposals__date__gte=knesset_start_date)
        return cms_date_filter, proposal_date_filter, vote_date_filter


class TagAwareMixin:
    def _get_tag(self):
        tag_id = self.kwargs.get('pk', None)
        return Tag.objects.get(pk=int(tag_id))


class CommitteeMeetingMoreView(GetMoreView, knessetAwareMixin, TagAwareMixin):
    paginate_by = 5
    template_name = 'ok_tag/tagged_committee_more_items.html'

    def _resolve_date_filter(self, knesset):
        knesset_end_date = knesset.end_date
        knesset_start_date = knesset.start_date
        if knesset_end_date is not None:
            cms_date_filter = Q(date__gte=knesset_start_date, date__lte=knesset_end_date)

        else:
            cms_date_filter = Q(date__gte=knesset_start_date)

        return cms_date_filter

    def get_queryset(self):
        knesset = self.get_knesset()
        cms_date_filter = self._resolve_date_filter(knesset=knesset)
        cms = CommitteeMeeting.committees_only.filter(cms_date_filter)

        tag = self._get_tag()
        filtered_cms = self._get_relevant_committee_meetings_by_tag(cms, tag)
        return filtered_cms

    def _get_relevant_committee_meetings_by_tag(self, cms, tag):
        cm_ct = ContentType.objects.get_for_model(CommitteeMeeting)
        cm_ids = TaggedItem.objects.filter(
            tag=tag, content_type=cm_ct).values_list('object_id', flat=True)
        cms = cms.filter(id__in=cm_ids).order_by('-date')
        return cms


def untagged_objects(request):
    return render_to_response('auxiliary/untagged_objects.html', {
        'cms': CommitteeMeeting.objects.filter_and_order(tagged=['false'])[:100],
        'cms_count': CommitteeMeeting.objects.filter_and_order(tagged=['false']).count(),
        'bills': Bill.objects.filter_and_order(tagged='false')[:100],
        'bill_count': Bill.objects.filter_and_order(tagged='false').count(),
        'votes': Vote.objects.filter_and_order(tagged='false')[:100],
        'vote_count': Vote.objects.filter_and_order(tagged='false').count(),
    },
                              context_instance=RequestContext(request))
