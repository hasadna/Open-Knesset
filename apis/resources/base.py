import csv

from django.conf import settings
from django.core.serializers import json
from django.http import HttpResponse
from tastypie.cache import SimpleCache
from tastypie.resources import ModelResource
from tastypie.throttle import CacheThrottle
from tastypie.serializers import Serializer

# are we using DummyCache ?
_cache = getattr(settings, 'CACHES', {})
_cache_default = _cache.get('default')
_is_dummy = _cache_default and _cache_default['BACKEND'].endswith('DummyCache')


class SmartCacheThrottle(CacheThrottle):
    "Make sure throttling works with DummyCache"

    def should_be_throttled(self, identifier, **kwargs):
        # Tastypie breaks when using dummy cache.  if cache type is dummy
        # we'll pretend the key wasn't found
        if _is_dummy:
            return False

        return super(SmartCacheThrottle, self).should_be_throttled(
            identifier, **kwargs)


class IterJSONAndCSVSerializer(Serializer):

    formats = Serializer.formats + ['csv']
    content_types = dict(
        Serializer.content_types.items() + [('csv', 'text/csv')]
    )

    def to_json(self, data, options=None):
        options = options or {}

        data = self.to_simple(data, options)
        return ''.join(json.DjangoJSONEncoder(sort_keys=True).iterencode(data))

    def to_csv(self, data, options=None):
        options = options or {}
        data = self.to_simple(data, options)
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=data.csv'

        response.write(u'\ufeff'.encode('utf8'))  # BOM for excel
        writer = csv.writer(response, dialect='excel')

        #   if data contains an 'objects' key, refer to it's value as a list of objects.
        #   else, treat data as a single object itself
        objects = data.get('objects', [data])
        for item in objects:
            writer.writerow([unicode(item[key]).encode(
                "utf-8", "replace") for key in item.keys()])
        return response


class BaseResource(ModelResource):

    """Adds to Meta the following options:

    * ``list_fields``: The fields to display in resources listing

    For list mode, on may add to ``extra_fields`` to GET params to get
    addtional comma separated field in case one need more fields than those
    specified in ``list_fields``. e.g:

        GET /api/v2/some_resource/?extra_fields=img_url,number_of_children
    """

    class Meta:
        cache = SimpleCache()
        throttle = SmartCacheThrottle(throttle_at=60, timeframe=60)
        serializer = IterJSONAndCSVSerializer(
            formats=['json', 'jsonp', 'xml', 'csv'])

    def _get_list_fields(self, request):
        """Helper to return list and extra fields for list mode.

        Make things easier for overriding.
        """

        field_names = getattr(self._meta, 'list_fields', None)
        if field_names:
            field_names = field_names[:]
            extra_fields = request.GET.get('extra_fields', None)

            if extra_fields:
                field_names.extend(x.strip() for x in extra_fields.split(',')
                                   if x.strip())
            if getattr(self._meta, 'include_resource_uri', False):
                field_names.append('resource_uri')
            if getattr(self._meta, 'include_absolute_url', False):
                field_names.append('absolute_url')

            fields = dict((name, obj) for name, obj in self.fields.iteritems()
                          if name in field_names)
        else:
            fields = None

        return fields

    def get_list(self, request, **kwargs):
        """
        Returns a serialized list of resources.

        We overide here, to add optional ``fields`` in calls to full_dehydrate
        in case the resource specifies ``list_fields`` (and optional
        ``extra_fields`` in GET).

        Calls ``obj_get_list`` to provide the data, then handles that result
        set and serializes it.

        Should return a HttpResponse (200 OK).
        """
        # TODO: Uncached for now. Invalidation that works for everyone may be
        #       impossible.
        base_bundle = self.build_bundle(request=request)
        objects = self.obj_get_list(bundle=base_bundle, **self.remove_api_resource_names(kwargs))
        sorted_objects = self.apply_sorting(objects, options=request.GET)

        paginator = self._meta.paginator_class(request.GET, sorted_objects, resource_uri=self.get_resource_uri(), limit=self._meta.limit, max_limit=self._meta.max_limit, collection_name=self._meta.collection_name)
        to_be_serialized = paginator.page()

        fields = self._get_list_fields(request)

        # Dehydrate the bundles in preparation for serialization.
        bundles = []

        for obj in to_be_serialized[self._meta.collection_name]:
            bundle = self.build_bundle(obj=obj, request=request)
            bundles.append(self.full_dehydrate(bundle, fields=fields))

        to_be_serialized[self._meta.collection_name] = bundles
        to_be_serialized = self.alter_list_data_to_serialize(request, to_be_serialized)
        return self.create_response(request, to_be_serialized)

    def full_dehydrate(self, bundle, for_list=False, fields=None):
        """
        Given a bundle with an object instance, extract the information from it
        to populate the resource.

        We override this to take into account optional fields in case of
        ``list``.
        """
        use_in = ['all', 'list' if for_list else 'detail']

        if fields is None:
            fields = self.fields

        # Dehydrate each field.
        for field_name, field_object in fields.items():
            # If it's not for use in this mode, skip
            field_use_in = getattr(field_object, 'use_in', 'all')
            if callable(field_use_in):
                if not field_use_in(bundle):
                    continue
            else:
                if field_use_in not in use_in:
                    continue

            # A touch leaky but it makes URI resolution work.
            if getattr(field_object, 'dehydrated_type', None) == 'related':
                field_object.api_name = self._meta.api_name
                field_object.resource_name = self._meta.resource_name

            bundle.data[field_name] = field_object.dehydrate(bundle)

            # Check for an optional method to do further dehydration.
            method = getattr(self, "dehydrate_%s" % field_name, None)

            if method:
                bundle.data[field_name] = method(bundle)

        bundle = self.dehydrate(bundle)
        return bundle
