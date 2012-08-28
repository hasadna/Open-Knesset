'''
Api for the members app
'''
import urllib
from django.core.urlresolvers import reverse
from tastypie.constants import ALL
from tastypie.bundle import Bundle
import tastypie.fields as fields

from tagging.models import Tag
from tagging.utils import calculate_cloud
from knesset.api.resources.base import BaseResource
from mks.models import Member, Party
from agendas.models import Agenda
from video.utils import get_videos_queryset
from video.api import VideoResource
from links.models import Link
from links.api import LinkResource

class PartyResource(BaseResource):
    ''' Party API
    TBD: create a party app
    '''

    class Meta:
        queryset = Party.objects.all()
        allowed_methods = ['get']
        excludes = ['end_date', 'start_date']
        include_absolute_url = True

class DictStruct:
    def __init__(self, **entries): 
            self.__dict__.update(entries)

class MemberBillsResource(BaseResource):

    class Meta:
        allowed_methods = ['get']
        resource_name = "member-bills"
        # object_class= DictStruct

    id = fields.IntegerField(attribute='id')
    bills = fields.ListField(attribute='bills')
    tag_cloud = fields.ListField(attribute='tag_cloud')

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            'resource_name': self._meta.resource_name,
        }
        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)

    def get_member_data(self, member):
        bills_tags = Tag.objects.usage_for_queryset(member.bills.all(),counts=True)
        tag_cloud = map(lambda x: dict(size=x.font_size, count=x.count, name=x.name),
                        calculate_cloud(bills_tags))
        bills  = map(lambda b: dict(title=b.full_title, 
                                    url=b.get_absolute_url(),
                                    stage=b.stage, 
                                    stage_text=b.get_stage_display()), 
                     member.bills.all())
        return DictStruct(id=member.id, tag_cloud=tag_cloud,bills=bills)

    def get_object_list(self, request):
        return map(self.get_member_data, Member.objects.all())

    def obj_get_list(self, request=None, **kwargs):
        # Filtering disabled for brevity...
        return self.get_object_list(request)

    def obj_get(self, request=None, **kwargs):
        member = Member.objects.get(pk=kwargs['pk'])
        return self.get_member_data(member)

class MemberAgendasResource(BaseResource):
    ''' The Parliament Member Agenda-compliance API '''
    class Meta:
        queryset = Member.objects.all()
        allowed_methods = ['get']
        fields = ['agendas'] # We're not really interested in any member details here
        resource_name = "member-agendas"

    def dehydrate(self, bundle):
        mk = bundle.obj
        agendas_values = mk.get_agendas_values()
        friends = mk.current_party.current_members().values_list('id', flat=True)
        agendas = []
        for a in Agenda.objects.filter(pk__in = agendas_values.keys(),
                is_public = True):
            amin = 200.0 ; amax = -200.0
            pmin = 200.0 ; pmax = -200.0
            av = agendas_values[a.id]
            for mk_id, values in a.get_mks_values():
                score = values['score']
                if score < amin:
                    amin = score
                if score > amax:
                    amax = score
                if mk_id in friends:
                    if score < pmin:
                        pmin = score
                    if score > pmax:
                        pmax = score

            agendas.append(dict(name = a.name,
                id = a.id,
                owner = a.public_owner_name,
                score = av['score'],
                rank = av['rank'],
                min = amin,
                max = amax,
                party_min = pmin,
                party_max = pmax,
                absolute_url = a.get_absolute_url(),
                ))
        bundle.data['agendas'] = agendas
        return bundle

class MemberResource(BaseResource):
    ''' The Parliament Member API '''
    class Meta:
        queryset = Member.objects.all().select_related('current_party')
        allowed_methods = ['get']
        ordering = [
            'name',
            'is_current',
            'bills_stats_proposed',
            'bills_stats_pre',
            'bills_stats_first',
            'bills_stats_approved',
            ]
        filtering = dict(
            name = ALL,
            is_current = ALL,
            )
        exclude_from_list_view = ['about_video_id','related_videos_uri',
                'links', 'videos']
        excludes = ['website', 'backlinks_enabled', 'area_of_residence']

    party_name = fields.CharField()
    party_url = fields.CharField()

    videos = fields.ToManyField(VideoResource,
                    attribute= lambda b: get_videos_queryset(b.obj),
                    null = True)
    links = fields.ToManyField(LinkResource,
                    attribute = lambda b: Link.objects.for_model(b.obj),
                    full = True,
                    null = True)
    bills_uri = fields.CharField()
    agendas_uri = fields.CharField()

    def dehydrate_bills_uri(self, bundle):
        return '%s?%s' % (reverse('api_dispatch_list', kwargs={'resource_name': 'bill',
                                                    'api_name': 'v2', }),
                          urllib.urlencode(dict(proposer=bundle.obj.id)))
    def dehydrate_gender(self, bundle):
        return bundle.obj.get_gender_display()

    def dehydrate_agendas_uri(self, bundle):
        return reverse('api_dispatch_detail', kwargs={'resource_name': 'member-agendas',
                                                    'api_name': 'v2',
                                                    'pk' : bundle.obj.id})
    def dehydrate_party_name(self, bundle):
        return bundle.obj.current_party.name

    def dehydrate_party_url(self, bundle):
        return bundle.obj.current_party.get_absolute_url()

    fields.ToOneField(PartyResource, 'current_party', full=True)

