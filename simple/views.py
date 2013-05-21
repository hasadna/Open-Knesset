from django.http import HttpResponse
from django.shortcuts import render_to_response

from models import HttpResponse

def hello_world(request):
    return HttpResponse('hello world')
