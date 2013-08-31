'''
Api for the members app
'''
import urllib
from django.core.urlresolvers import reverse
from django.core.cache import cache
from tastypie.constants import ALL
from tastypie.bundle import Bundle
import tastypie.fields as fields

from tagging.models import Tag
from tagging.utils import calculate_cloud
from apis.resources.base import BaseResource
from models import Member, Party, Knesset
from agendas.models import Agenda
from video.utils import get_videos_queryset
from video.api import VideoResource
from links.models import Link
from links.api import LinkResource

from django.db.models import Count

class PartyResource(BaseResource):
    ''' Party API
    TBD: create a party app
    '''

    class Meta(BaseResource.Meta):
        queryset = Party.objects.filter(
            knesset=Knesset.objects.current_knesset()
            )
        allowed_methods = ['get']
        excludes = ['end_date', 'start_date']
        include_absolute_url = True

class DictStruct:
    def __init__(self, **entries):
            self.__dict__.update(entries)

class MemberBillsResource(BaseResource):

    class Meta(BaseResource.Meta):
        allowed_methods = ['get']
        resource_name = "member-bills"
        # object_class= DictStruct

    id = fields.IntegerField(attribute='id')
    bills = fields.ListField(attribute='bills')
    tag_cloud = fields.ListField(attribute='tag_cloud')

    def get_resource_uri(self, bundle_or_obj=None, url_name='api_dispatch_list'):
        kwargs = {
            'resource_name': self._meta.resource_name,
        }

        if bundle_or_obj is not None:
            if isinstance(bundle_or_obj, Bundle):
                kwargs['pk'] = bundle_or_obj.obj.id
            else:
                kwargs['pk'] = bundle_or_obj.id

            url_name = 'api_dispatch_detail'

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return self._build_reverse_url(url_name, kwargs=kwargs)

    def get_member_data(self, member):
        bills_tags = Tag.objects.usage_for_queryset(member.bills.all(),
                                                    counts=True)
        # we'll use getattr for font_size, as it might not always be there
        # This prevents the need of using a forked django-tagging, and go
        # upstream
        tag_cloud = [{
            'size': getattr(x, 'font_size', 1),
            'count':x.count,
            'name':x.name} for x in calculate_cloud(bills_tags)]

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

    agendas = fields.ListField()

    class Meta(BaseResource.Meta):
        queryset = Member.objects.select_related('current_party').order_by()
        allowed_methods = ['get']
        fields = ['agendas']  # We're not really interested in any member details here
        resource_name = "member-agendas"

    def dehydrate_agendas(self, bundle):
        mk = bundle.obj
        _cache_key = 'api_v2_member_agendas_' + str(mk.pk)
        agendas = cache.get(_cache_key)

        if not agendas:
            agendas_values = mk.get_agendas_values()
            friends = mk.current_party.current_members().values_list('id', flat=True).order_by()
            agendas = []
            for a in Agenda.objects.filter(pk__in = agendas_values.keys(),
                    is_public = True):
                amin = 200.0 ; amax = -200.0
                pmin = 200.0 ; pmax = -200.0
                av = agendas_values[a.id]
                for mk_id, values in a.get_mks_values_old():
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

                agendas.append(dict(
                    name=a.name,
                    id=a.id,
                    owner=a.public_owner_name,
                    score=av['score'],
                    rank=av['rank'],
                    min=amin,
                    max=amax,
                    party_min=pmin,
                    party_max=pmax,
                    absolute_url=a.get_absolute_url(),
                ))

            cache.set(_cache_key, agendas, 24 * 3600)

        return agendas


class MemberResource(BaseResource):
    ''' The Parliament Member API '''
    class Meta(BaseResource.Meta):

        queryset = Member.objects.exclude(
            current_party__isnull=True).select_related('current_party')

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
            name=ALL,
            is_current=ALL,
        )

        excludes = ['website', 'backlinks_enabled', 'area_of_residence']
        list_fields = ['name', 'id', 'img_url', 'is_current']
        include_absolute_url = True

    party_name = fields.CharField()
    party_url = fields.CharField()
    mmms_count = fields.IntegerField(null=True)
    votes_count = fields.IntegerField(null=True)
    video_about =  fields.ToManyField(VideoResource,
                    attribute= lambda b: get_videos_queryset(b.obj,group='about'),
                    null = True,
                    full = True)
    videos_related = fields.ToManyField(VideoResource,
                    attribute= lambda b: get_videos_queryset(b.obj,group='related'),
                    null = True)
    links = fields.ToManyField(LinkResource,
                    attribute = lambda b: Link.objects.for_model(b.obj),
                    full = True,
                    null = True)
    bills_uri = fields.CharField()
    agendas_uri = fields.CharField()
    committees = fields.ListField()

    def dehydrate_committees (self, bundle):
        temp_list = bundle.obj.committee_meetings.values("committee", "committee__name").annotate(Count("id")).order_by('-id__count')[:5]
        return (map(lambda item: (item['committee__name'], reverse('committee-detail', args=[item['committee']])), temp_list))

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

    def dehydrate_mmms_count(self, bundle):
        _cache_key = 'api_v2_member_mmms_' + str(bundle.obj.pk)
        count = cache.get(_cache_key)

        if count is None:
            count = bundle.obj.mmm_documents.count()
            cache.set(_cache_key, count, 24 * 3600)

        return count

    def dehydrate_votes_count(self, bundle):
        _cache_key = 'api_v2_member_votes_' + str(bundle.obj.pk)
        count = cache.get(_cache_key)

        if count is None:
            count = bundle.obj.votes.count()
            cache.set(_cache_key, count, 24 * 3600)

        return count

    fields.ToOneField(PartyResource, 'current_party', full=True)

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}

        try:
            knesset = int(filters.get('knesset', 0))
        except KeyError:
            knesset = 0

        orm_filters = super(MemberResource, self).build_filters(filters)

        if knesset:
            knesset = Knesset.objects.get(number=knesset)
            orm_filters['parties__knesset'] = knesset

        return orm_filters
