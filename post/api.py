'''
Api for planet
'''

from tastypie.exceptions import InvalidFilterError
from tastypie.constants import ALL
from apis.resources.base import BaseResource
from planet.models import Feed, Post
from mks.models import Member
from links.models import Link


class PostResource(BaseResource):

    class Meta:
        limit = 50
        allowed_methods = ['get']
        fields = ['id', 'title', 'date_created', 'url', 'content']

        queryset = Post.objects.all()
        resource_name = "posts"
        filtering = {
            'member_id': ALL,
        }

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}

        orm_filters = super(PostResource, self).build_filters(filters)

        if "member_id" in filters:
            try:
                member = Member.objects.get(pk=filters['member_id'])
            except Member.DoesNotExist:
                raise InvalidFilterError("Could not find member id %s" % filters['member_id'])
            links = Link.objects.for_model(member)
            feeds = Feed.objects.filter(url__in=map(lambda x: x.url, links), is_active=True)

            orm_filters["feed__in"] = feeds

        return orm_filters
