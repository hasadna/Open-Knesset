from logging import getLogger

from django.http.response import HttpResponse, HttpResponseBadRequest
import requests

KIKAR_URL_BASE = 'http://www.kikar.org'
logger = getLogger(__name__)


def get_statuses(request):
    request_params = request.GET.dict()
    request_path = request_params.get('request_path')
    if not request_path:
        return HttpResponseBadRequest("Bad request: missing request_path param")

    url = KIKAR_URL_BASE + request_params.pop('request_path')
    if 'filter' in request_params:
        request_filter = request_params.pop('filter').split('=')
        request_params[request_filter[0]] = request_filter[1]

    # TODO: Jesus how can this be even tested? should be separated to proxy
    kikar_res = requests.get(url,
                             params=request_params)
    logger.debug(kikar_res.url)
    res = HttpResponse(content=kikar_res.content, content_type='application/json')
    return res

    # Member: http://localhost:8000/api/v1/facebook_status/?limit=14&feed__persona__object_id=878&order_by=-published
    # Party: http://localhost:8000/api/v1/facebook_status/?limit=4&feed__persona__object_id__in=782,878&order_by=-published
    # Tag: http://localhost:8000/api/v1/facebook_status/?limit=14&feed__is_current=true&content__contains=%D7%97%D7%A7%D7%9C%D7%90%D7%95%D7%AA


def get_member(request, **kwargs):
    url = KIKAR_URL_BASE + '/api/v1/member/' + kwargs['pk']
    logger.debug(url)
    kikar_res = requests.get(url)
    logger.debug(kikar_res.url)
    res = HttpResponse(content=kikar_res.content, content_type='application/json')
    return res
