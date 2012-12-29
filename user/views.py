from datetime import datetime, timedelta

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, \
                        HttpResponseServerError, HttpResponseBadRequest, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist


from annotatetext.models import Annotation
from actstream import unfollow, follow
from actstream.models import Action, Follow

from accounts.models import EmailValidation
from mks.models import Member
from laws.models import Bill
from agendas.models import Agenda
from tagvotes.models import TagVote
from committees.models import CommitteeMeeting,Topic

from forms import RegistrationForm, EditProfileForm

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
            'annotations': Annotation.objects.filter(user=user).order_by('content_type', 'object_id'),
            'tagged_items': TagVote.objects.filter(user=user).order_by('tagged_item__content_type','tagged_item__object_id'),
            'agendas': [a for a in user.get_profile().agendas if a.is_public],
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

def user_follow_unfollow(request):
    """Recieves POST parameters:
        verb - 'follow' or 'unfollow'
        what - string representing target object type ('member', 'agenda', ...)
        id - id of target object
        """
    if not request.user.is_authenticated():
        return HttpResponseForbidden(reverse('login'))
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    target_id = request.POST.get('id', None)
    if not target_id:
        return HttpResponseBadRequest('need an id of an object to watch')
    what = request.POST.get('what', None)
    what_types = { # these are the object types we allow following
        'member': Member,
        'meeting': CommitteeMeeting,
        'agenda': Agenda,
        'bill': Bill,
        'topic': Topic,
    }
    if what not in what_types:
        return HttpResponseBadRequest(
            'what parameter has to be one of: %s' % ','.join(what_types.keys()))
    verb = request.POST.get('verb', None)
    if verb not in ['follow','unfollow']:
        return HttpResponseBadRequest(
            "verb parameter has to be one of: 'follow', 'unfollow'")
    if verb == 'follow':
        try:
            obj = get_object_or_404(what_types[what], pk=target_id)
            follow(request.user, obj)
        except:
            return HttpResponseBadRequest('object not found')
    else: # unfollow
        content_type = ContentType.objects.get_for_model(what_types[what])
        Follow.objects.get(user=request.user,
            content_type=content_type, object_id=target_id).delete()

    return HttpResponse('OK')

def user_is_following(request):
    """Recieves POST parameters:
        what - string representing target object type ('member', 'agenda', ...)
        id - id of target object
        """
    if not request.user.is_authenticated():
        return HttpResponse('false')
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    target_id = request.POST.get('id', None)
    if not target_id:
        return HttpResponseBadRequest('need an id of an object to watch')
    what = request.POST.get('what', None)
    what_types = { # these are the object types we allow following
        'member': Member,
        'meeting': CommitteeMeeting,
        'agenda': Agenda,
        'bill': Bill,
        'topic': Topic,
    }
    if what not in what_types:
        return HttpResponseBadRequest(
            'what parameter has to be one of: %s' % ','.join(what_types.keys()))
            
    content_type = ContentType.objects.get_for_model(what_types[what])
    try:
        Follow.objects.get(user=request.user,
            content_type=content_type, object_id=target_id)
        return HttpResponse('true')
    except ObjectDoesNotExist:
        return HttpResponse('false')
