from django.conf.urls import url, patterns, include

from resources import v2_api

urlpatterns = patterns(
    '',
    (r'^', include(v2_api.urls)),
    url(
        r'^v2/doc/',
        include('tastypie_swagger.urls', namespace='tastypie_swagger'),
        kwargs={
            "tastypie_api_module": "apis.resources.v2_api",
            "namespace": "tastypie_swagger", "version": "2.0"
        }
    ),
    url(
        r'knesset-data/',
        include('knesset_data_django.api.urls', namespace='knesset_data_django')
    )
)
