'''
API for the agendas app
'''
from django.contrib.auth.models import User
from tastypie.constants import ALL
import tastypie.fields as fields
from avatar.templatetags.avatar_tags import avatar_url

from knesset.api.resources.base import BaseResource
from knesset.mks.models import Member, Party
from knesset.agendas.models import Agenda, AgendaVote

class UserResource(BaseResource):
    class Meta(BaseResource.Meta):
        queryset = User.objects.all()
        include_absolute_url = True
        include_resource_uri = False
        allowed_methods = ['get']
        fields = ['username']

    avatar = fields.CharField()

    def dehydrate_avatar(self, bundle):
        return avatar_url(bundle.obj, 48)

class AgendaVoteResource(BaseResource):
    class Meta(BaseResource.Meta):
        object_class = AgendaVote
        allowed_methods = ['get']

    title = fields.CharField()

    def dehydrate_title(self, bundle):
        return bundle.obj.vote.title

class AgendaTodoResource(BaseResource):
    class Meta(BaseResource.Meta):
        allowed_methods = ['get']
        queryset = Agenda.objects.all()
        resource_name = 'agenda-todo'
        fields = ['votes_by_conrtoversy', 'votes_by_agendas']
    
    votes_by_controversy = fields.ListField()
    votes_by_agendas = fields.ListField()
    
    # TODO: Make this a parameter or setting or something
    NUM_SUGGESTIONS = 10
    
    def dehydrate_votes_by_agendas(self, bundle):
        votes = bundle.obj.get_suggested_votes_by_agendas(AgendaTodoResource.NUM_SUGGESTIONS)
        return self._dehydrate_votes(votes)

    def dehydrate_votes_by_controversy(self, bundle):
        votes = bundle.obj.get_suggested_votes_by_controversy(AgendaTodoResource.NUM_SUGGESTIONS)
        return self._dehydrate_votes(votes)

    def _dehydrate_votes(self, votes):
        def dehydrate_vote(vote):
            return dict(id=vote.id,
                        url=vote.get_absolute_url(),
                        title=vote.title,
                        score=vote.score)
        return [dehydrate_vote(v) for v in votes]

class AgendaResource(BaseResource):
    ''' Agenda API '''
    class Meta(BaseResource.Meta):
        queryset = Agenda.objects.filter(is_public=True)
        allowed_methods = ['get']
        include_absolute_url = True
        excludes = ['is_public']

    editors = fields.ToManyField(UserResource,
                    'editors',
                    full=True)
    votes = fields.ToManyField(AgendaVoteResource,
                    'agendavotes',
                    full=True)

    def dehydrate(self, bundle):
        a = bundle.obj
        mks_values = dict(a.get_mks_values())
        members = []
        for mk in Member.objects.filter(pk__in = mks_values.keys()).select_related('current_party'):
            # TODO: this sucks, performance wise
            current_party = mk.current_party
            members.append (dict(name=mk.name,
                    score = mks_values[mk.id]['score'],
                    rank = mks_values[mk.id]['rank'],
                    absolute_url = mk.get_absolute_url(),
                    party = current_party.name,
                    party_url = current_party.get_absolute_url(),
                ))
        bundle.data['members'] = members
        bundle.data['parties'] = map(
                lambda x: dict(name=x.name, score=a.party_score(x),
                    absolute_url=x.get_absolute_url()),
                Party.objects.all())
        return bundle
