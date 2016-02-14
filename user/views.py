from datetime import datetime, timedelta
import json
import urllib2

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, \
                        HttpResponseServerError, HttpResponseBadRequest, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login as authlogin, logout_then_login as authlogout_then_login
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_http_methods
from django.conf import settings
import jwt

from annotatetext.models import Annotation
from actstream import unfollow, follow
from actstream.models import Action, Follow

from accounts.models import EmailValidation
from mks.models import Member
from laws.models import Bill
from agendas.models import Agenda
from tagvotes.models import TagVote
from committees.models import CommitteeMeeting,Topic
from user.models import UserCustomMetadata

from forms import RegistrationForm, EditProfileForm
from django.views.decorators.csrf import csrf_exempt
from utils import parse_signed_request


class PublicUserProfile(DetailView):
    model = User
    template_resource_name = 'viewed_user' # can't be 'user' because that name is
                                           # overriden by request context processor!
    slug_field='username'
    context_object_name = 'viewed_user'

    def get_context_data(self, **kwargs):
        context = super(PublicUserProfile, self).get_context_data(**kwargs)
        user = self.object
        context.update({
            'annotations': Annotation.objects.filter(user=user).prefetch_related('content_object').order_by('content_type', 'object_id'),
            'tagged_items': TagVote.objects.filter(user=user).order_by('tagged_item__content_type','tagged_item__object_id'),
            'agendas': [a for a in user.profiles.get().agendas if a.is_public],
            'topics': Topic.objects.get_public().filter(creator=user),
        })
        return context


class ProfileListView(ListView):

    queryset = User.objects.order_by('username').filter(profiles__public_profile=True)
    template_name = 'user/profile_list.html'

class AggregatedAction:
    def __init__(self, actor, verb):
        self.actor = actor
        self.verb = verb
        self.targets = {}
        self.timestamp = datetime.now()

    def __str__(self):
        return self.actor.__str__()+" "+self.verb.__str__()+" "+self.targets.__str__()

AGGREGATION_BREAK_PERIOD = timedelta(0, 15*60) #15 minutes

def aggregate_stream(actions):
    aggr_stream = []

    aggr_action = None
    for action in actions:
        if aggr_action is None: # first item in the action list
            pass
        elif aggr_action.verb != action.verb or aggr_action.actor != action.actor or (aggr_action.timestamp-action.timestamp)>AGGREGATION_BREAK_PERIOD:
            # break aggregation
            aggr_stream.append(aggr_action)
        elif aggr_action.targets.has_key(action.target):
            aggr_action.targets[action.target] += 1
            continue
        else:
            aggr_action.targets[action.target] = 1;
            continue

        # create a new aggregated action based on the current action
        aggr_action = AggregatedAction(action.actor, action.verb)
        aggr_action.targets[action.target] = 1
        aggr_action.timestamp = action.timestamp

    # add the last aggregated action to the stream
    if aggr_action is not None:
        aggr_stream.append(aggr_action)

    return aggr_stream

def create_user(request):
    if request.method == 'POST':
        form = RegistrationForm(data=request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(username=form.cleaned_data['username'],
                                password=form.cleaned_data['password1'])
            login(request, user)
            EmailValidation.objects.send(user=user)
            next = request.POST.get('next', None)
            return HttpResponseRedirect(next if next else reverse('edit-profile'))
        else:
            return render_to_response('user/create_user.html',
                        context_instance=RequestContext(request, {'form': form}))
    form = RegistrationForm()
    return render_to_response('user/create_user.html',
                context_instance=RequestContext(request, {'form': form,
                    'next': request.GET.get('next','')}))

@login_required
def edit_profile(request):
    if request.method == 'POST':
        edit_form = EditProfileForm(user=request.user, data=request.POST)
        if edit_form.is_valid():
            edit_form.save()
            messages.add_message(request,
                                 messages.INFO,
                                 _('Your profile has been updated.')
                                )
            return HttpResponseRedirect('.')

    if request.method == 'GET':
        edit_form = EditProfileForm(user = request.user)
    return render_to_response('user/editprofile.html',
        context_instance=RequestContext(request,
            {'edit_form': edit_form,
            }))

# these are the object types we allow following
FOLLOW_TYPES = {
    'member': Member,
    'meeting': CommitteeMeeting,
    'agenda': Agenda,
    'bill': Bill,
    'topic': Topic,
}


@require_http_methods(['POST'])
def user_follow_unfollow(request):
    """Recieves POST parameters:

    verb - 'follow' or 'unfollow'
    what - string representing target object type ('member', 'agenda', ...)
    id - id of target object

    """
    what = request.POST.get('what', None)
    if what not in FOLLOW_TYPES:
        return HttpResponseBadRequest(
            'what parameter has to be one of: %s' % ','.join(FOLLOW_TYPES.keys()))

    if not request.user.is_authenticated():
        return HttpResponseForbidden(reverse('login'))

    target_id = request.POST.get('id', None)
    if not target_id:
        return HttpResponseBadRequest('need an id of an object to watch')

    verb = request.POST.get('verb', None)
    if verb not in ['follow', 'unfollow']:
        return HttpResponseBadRequest(
            "verb parameter has to be one of: 'follow', 'unfollow'")

    logged_in = request.user.is_authenticated()
    content_type = ContentType.objects.get_for_model(FOLLOW_TYPES[what])
    qs = Follow.objects.filter(object_id=target_id, content_type=content_type)

    if verb == 'follow':
        try:
            obj = get_object_or_404(FOLLOW_TYPES[what], pk=target_id)
            follow(request.user, obj)
        except:
            return HttpResponseBadRequest('object not found')
    else:  # unfollow
        Follow.objects.get(
            user=request.user,
            content_type=content_type, object_id=target_id).delete()

    res = {
        'can_watch': logged_in,
        'followers': qs.count(),
        'watched': logged_in and bool(qs.filter(user=request.user))
    }
    return HttpResponse(json.dumps(res), content_type='application/json')


def user_is_following(request):
    """Recieves GET parameters:

    what - string representing target object type ('member', 'agenda', ...)
    id - id of target object

    """
    what = request.GET.get('what', None)

    if what not in FOLLOW_TYPES:
        return HttpResponseBadRequest(
            'what parameter has to be one of: %s' % ','.join(FOLLOW_TYPES.keys()))

    target_id = request.GET.get('id', None)
    if not target_id:
        return HttpResponseBadRequest('need an id of an object to watch')

    content_type = ContentType.objects.get_for_model(FOLLOW_TYPES[what])

    logged_in = request.user.is_authenticated()
    qs = Follow.objects.filter(object_id=target_id, content_type=content_type)

    res = {
        'can_watch': logged_in,
        'followers': qs.count(),
        'watched': logged_in and bool(qs.filter(user=request.user))
    }

    return HttpResponse(json.dumps(res), content_type='application/json')

def login_view(request, *args, **kwargs):
    is_iframe = request.GET.get('is_iframe', '') == '1' or request.POST.get('is_iframe', '') == '1'
    if is_iframe and request.user.is_authenticated():
       logout(request)
    kwargs['extra_context'] = {
        'is_iframe': is_iframe
    }
    return authlogin(request, *args, **kwargs)

def login_redirect(request, target):
    target_settings = settings.LOGIN_REDIRECT_TARGETS[target]
    if request.user.is_authenticated() and not request.user.is_anonymous():
        payload = {
            'user_id': request.user.pk,
            'email': request.user.email,
            'username': request.user.username,
            'exp': datetime.utcnow() + settings.JWT_EXPIRATION_DELTA
        }
        token = jwt.encode(payload, settings.SECRET_KEY, settings.JWT_ALGORITHM).decode('utf-8')
    else:
        token = ''
    return HttpResponse('<script>if (parent == window) {window.location.href = "'+target_settings['parent_location_href']+token+'"} else {parent.postMessage("'+token+'", "'+target_settings['redirect_to_url']+'");};</script>')

@csrf_exempt
@require_http_methods(['POST'])
def fbstore(request, target):
    secret = settings.LOGIN_REDIRECT_TARGETS['opensubs']['fb_secret']
    data = json.loads(request.body)
    signedRequest = data['signedRequest']
    accessToken = data['accessToken']
    k = data['k']
    v = data['v']
    fb = parse_signed_request(signedRequest, secret)
    if fb is None:
        return HttpResponse('%s: ERROR'%target)
    else:
        fb_user_id = fb['user_id']
        fbuser = json.loads(urllib2.urlopen('https://graph.facebook.com/me?fields=id,email&access_token=%s'%accessToken).read(1000))
        if fbuser['id'] != fb_user_id:
            return HttpResponse('%s: ERROR'%target)
        else:
            email = fbuser['email']
            user, is_created = User.objects.get_or_create(email=email)
            user.get_profile().custom_metadata.add(UserCustomMetadata(app_id=target, k=k, v=v))
            return HttpResponse('%s: OK'%target)
