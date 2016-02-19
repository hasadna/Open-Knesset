import logging
import random
from datetime import timedelta

from annotatetext.views import post_annotation as annotatetext_post_annotation
from django.conf import settings
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.http import (
    HttpResponseForbidden, HttpResponseRedirect)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, DetailView, ListView
from okscraper_django.models import ScraperRun

from committees.models import CommitteeMeeting
from events.models import Event
from laws.models import Vote, Bill
from mks.models import Member

from .forms import TidbitSuggestionForm, FeedbackSuggestionForm
from .models import Tidbit


class MainScraperStatusView(ListView):
    queryset = ScraperRun.objects.all().filter(start_time__gt=timezone.now() - timedelta(days=30)).order_by(
        '-start_time')
    template_name = 'auxiliary/main_scraper_status.html'

    def get_context_data(self, *args, **kwargs):
        context = super(ListView, self).get_context_data(*args, **kwargs)
        for object in context['object_list']:
            status = 'SUCCESS'
            failedLogs = object.logs.exclude(status='INFO')
            if failedLogs.count() > 0:
                status = failedLogs.order_by('-id')[0].status
            object.status = status
        return context


class ScraperRunDetailView(DetailView):
    model = ScraperRun
    template_name = 'auxiliary/scraper_run_detail.html'


logger = logging.getLogger("open-knesset.auxiliary.views")


def help_page(request):
    context = cache.get('help_page_context')
    if not context:
        context = {}
        context['title'] = _('Help')
        context['member'] = Member.current_knesset.all()[random.randrange(Member.current_knesset.count())]
        votes = Vote.objects.filter_and_order(order='controversy')
        context['vote'] = votes[random.randrange(votes.count())]
        context['bill'] = Bill.objects.all()[random.randrange(Bill.objects.count())]

        tags_cloud = cache.get('tags_cloud', None)
        if not tags_cloud:
            # TODO: ugly hack, remove this import later, when I figure out why this is even needed here
            from ok_tag.views import calculate_cloud_from_models
            tags_cloud = calculate_cloud_from_models(Vote, Bill, CommitteeMeeting)
            tags_cloud.sort(key=lambda x: x.name)
            cache.set('tags_cloud', tags_cloud, settings.LONG_CACHE_TIME)
        context['tags'] = random.sample(tags_cloud,
                                        min(len(tags_cloud), 8)
                                        ) if tags_cloud else None
        context['has_search'] = False  # enable the base template search
        cache.set('help_page_context', context, 300)  # 5 Minutes
    template_name = '%s.%s%s' % ('help_page', settings.LANGUAGE_CODE, '.html')
    return render_to_response(template_name, context, context_instance=RequestContext(request))


def add_previous_comments(comments):
    previous_comments = set()
    for c in comments:
        c.previous_comments = Comment.objects.filter(
            object_pk=c.object_pk,
            content_type=c.content_type,
            submit_date__lt=c.submit_date).select_related('user')
        previous_comments.update(c.previous_comments)
        c.is_comment = True
    comments = [c for c in comments if c not in previous_comments]
    return comments


def get_annotations(comments, annotations):
    for a in annotations:
        a.submit_date = a.timestamp
    comments = add_previous_comments(comments)
    annotations.extend(comments)
    annotations.sort(key=lambda x: x.submit_date, reverse=True)
    return annotations


def main(request):
    """
    Note on annotations:
     Old:
        Return annotations by concatenating Annotation last 10 and Comment last
        10, adding all related comments (comments on same item that are older).
        annotations_old = get_annotations(
            annotations=list(Annotation.objects.all().order_by('-timestamp')[:10]),
            comments=Comment.objects.all().order_by('-submit_date')[:10])
     New:
        Return annotations by Action filtered to include only:
         annotation-added (to meeting), ignore annotated (by user)
         comment-added
    """
    # context = cache.get('main_page_context')
    # if not context:
    #    context = {
    #        'title': _('Home'),
    #        'hide_crumbs': True,
    #    }
    #    actions = list(main_actions()[:10])
    #
    #    annotations = get_annotations(
    #        annotations=[a.target for a in actions if a.verb != 'comment-added'],
    #        comments=[x.target for x in actions if x.verb == 'comment-added'])
    #    context['annotations'] = annotations
    #    b = get_debated_bills()
    #    if b:
    #        context['bill'] = get_debated_bills()[0]
    #    else:
    #        context['bill'] = None
    #    public_agenda_ids = Agenda.objects.filter(is_public=True
    #                                             ).values_list('id',flat=True)
    #    if len(public_agenda_ids) > 0:
    #        context['agenda_id'] = random.choice(public_agenda_ids)
    #    context['topics'] = Topic.objects.filter(status__in=PUBLIC_TOPIC_STATUS)\
    #                                     .order_by('-modified')\
    #                                     .select_related('creator')[:10]
    #    cache.set('main_page_context', context, 300) # 5 Minutes

    # did we post the TidbitSuggest form ?
    if request.method == 'POST':
        # only logged-in users can suggest
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        form = TidbitSuggestionForm(request.POST)
        if form.is_valid():
            form.save(request)

        return form.get_response()

    NUMOF_EVENTS = 8
    events = Event.objects.get_upcoming()

    # Reduce the number of sql queries, by prefetching the objects and setting
    # them on the objects
    upcoming = list(events[:NUMOF_EVENTS])

    generics = {}
    for item in upcoming:
        if item.which_pk:
            generics.setdefault(item.which_type_id, set()).add(item.which_pk)

    content_types = ContentType.objects.in_bulk(generics.keys())

    relations = {}
    for ct, fk_list in generics.items():
        ct_model = content_types[ct].model_class()
        relations[ct] = ct_model.objects.in_bulk(list(fk_list))

    for item in upcoming:
        if item.which_pk:
            setattr(item, '_which_object_cache',
                    relations[item.which_type_id].get(item.which_pk))

    context = {
        'title': _('Home'),
        'hide_crumbs': True,
        'is_index': True,
        'tidbits': Tidbit.active.all().order_by('?'),
        'suggestion_forms': {'tidbit': TidbitSuggestionForm()},
        'events': upcoming,
        'INITIAL_EVENTS': NUMOF_EVENTS,
        'events_more': events.count() > NUMOF_EVENTS,
    }
    template_name = '%s.%s%s' % ('main', settings.LANGUAGE_CODE, '.html')
    return render_to_response(template_name, context,
                              context_instance=RequestContext(request))


@require_http_methods(['POST'])
def post_feedback(request):
    "Post a feedback suggestion form"
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    form = FeedbackSuggestionForm(request.POST)
    if form.is_valid():
        form.save(request)

    return form.get_response()


def post_annotation(request):
    if request.user.has_perm('annotatetext.add_annotation'):
        return annotatetext_post_annotation(request)
    else:
        return HttpResponseForbidden(_("Sorry, you do not have the permission to annotate."))


def search(request, lang='he'):
    # remove the 'cof' get variable from the query string so that the page
    # linked to by the javascript fallback doesn't think its inside an iframe.
    mutable_get = request.GET.copy()
    if 'cof' in mutable_get:
        del mutable_get['cof']

    return render_to_response('search/search.html', RequestContext(request, {
        'query': request.GET.get('q'),
        'query_string': mutable_get.urlencode(),
        'has_search': True,
        'lang': lang,
        'cx': settings.GOOGLE_CUSTOM_SEARCH,
    }))


def post_details(request, post_id):
    ''' patching django-planet's post_detail view so it would update the
        hitcount and redirect to the post's url
    '''
    from hitcount.views import _update_hit_count
    from hitcount.models import HitCount
    from planet.models import Post

    # update the it count
    ctype = ContentType.objects.get(app_label="planet", model="post")
    hitcount, created = HitCount.objects.get_or_create(content_type=ctype,
                                                       object_pk=post_id)
    result = _update_hit_count(request, hitcount)
    post = get_object_or_404(Post, pk=post_id)
    return HttpResponseRedirect(post.url)


class RobotsView(TemplateView):
    """Return the robots.txt"""

    template_name = 'robots.txt'

    def render_to_response(self, context, **kwargs):
        return super(RobotsView, self).render_to_response(context,
                                                          content_type='text/plain', **kwargs)


class AboutView(TemplateView):
    """About template"""

    template_name = 'about.html'


class CommentsView(ListView):
    """Comments index view"""

    model = Comment
    queryset = Comment.objects.order_by("-submit_date")

    paginate_by = 20
