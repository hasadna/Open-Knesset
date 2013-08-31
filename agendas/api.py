'''
API for the agendas app
'''
from collections import defaultdict

from django.utils.timezone import datetime

import tastypie.fields as fields
from avatar.templatetags.avatar_tags import avatar_url
from django.contrib.auth.models import User

from models import Agenda, AgendaVote
from apis.resources.base import BaseResource
from mks.models import Member, Party

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
        queryset = AgendaVote.objects.select_related()
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

    def dehydrate_votes_by_agendas(self, bundle):
        return self._dehydrate_votes(bundle.obj.get_suggested_votes_by_agendas)

    def dehydrate_votes_by_controversy(self, bundle):
        return self._dehydrate_votes(bundle.obj.get_suggested_votes_by_controversy)

    # TODO: Make this a parameter or setting or something
    NUM_SUGGESTIONS = 10
    def _dehydrate_votes(self, select):
        return [{'id':vote.id,
                'url':vote.get_absolute_url(),
                'title':vote.title,
                'score':vote.score}
                for vote in select(AgendaTodoResource.NUM_SUGGESTIONS)]


class AgendaResource(BaseResource):
    ''' Agenda API '''

    members = fields.ListField()
    parties = fields.ListField()
    votes = fields.ListField()
    editors = fields.ListField()
    ranges = fields.ListField()

    class Meta(BaseResource.Meta):
        queryset = Agenda.objects.filter(
            is_public=True).prefetch_related('agendavotes__vote', 'editors')
        allowed_methods = ['get']
        include_absolute_url = True
        excludes = ['is_public']
        list_fields = ['name', 'id', 'description', 'public_owner_name']

    def dehydrate_ranges(self, bundle):
        for rangeString in bundle.request.GET.get('ranges', '-').split(','):
            start, end = rangeString.split('-')
            rangeResult = {}
            if start:
                rangeResult['from'] = _gettime(start)
            if end:
                rangeResult['to'] = _gettime(end)
            yield rangeResult
        
    def dehydrate_members(self, bundle):
        ranges = [
                    tuple(datetime.strptime(val, "%Y%m") if val else None for val in rangeString.split('-'))
                      for rangeString in bundle.request.GET.get('ranges', '-').split(',')]
        mks_values = dict(bundle.obj.get_mks_values(ranges))
        mks_list = Member.objects.filter(pk__in=set(mks_values.keys()),
                                            current_party__isnull=False).select_related('current_party')
        for mk in mks_list:
            yield dict( id=mk.id,
                        name=mk.name,
                        absolute_url=mk.get_absolute_url(),
                        party= mk.current_party.name,
                        party_url= mk.current_party.get_absolute_url(),
                        party_id= mk.current_party.pk,
                        **self._get_points(mks_values[mk.id]))

    @staticmethod                                   
    def _get_points(mk_data):
        # TODO: this sucks, performance wise
        if not isinstance(mk_data, list):
            mk_data = [mk_data]
        #zip(*matrix) is transpose(matrix)
        score, rank, volume, numvotes = zip(*[(x['score'], x['rank'], x['volume'], x['numvotes']) for x in mk_data])
        return {'score': score,
                'rank': rank,
                'volume': volume,
                'numvotes': numvotes}

    def dehydrate_parties(self, bundle):
        party_values = defaultdict(dict, {party_data[0]:{'score':party_data[1],'volume':party_data[2]}
                         for party_data in bundle.obj.get_party_values()})
        for party in Party.objects.all():
            yield dict(name=party.name,
                     absolute_url=party.get_absolute_url(),
                     **party_values[party.pk])

    def dehydrate_votes(self, bundle):
        for v in bundle.obj.agendavotes.select_related():
            yield {'title':v.vote.title,
                   'id':v.vote_id,
                   'importance':v.importance,
                   'score':v.score,
                   'reasoning':v.reasoning}

    def dehydrate_editors(self, bundle):
        for e in bundle.obj.editors.all():
            yield {'absolute_url':e.get_absolute_url(),
                  'username':e.username,
                  'avatar':avatar_url(e, 48)}

def _gettime(at):
    year, month = divmod(int(at), 100)
    return datetime(year=year, month=month, day=1)
