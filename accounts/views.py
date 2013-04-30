from django.conf import settings
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission

from models import EmailValidation

import logging
import sys,traceback
logger = logging.getLogger("open-knesset.accounts")



@login_required
def send_validation_email(request):
    if request.method == 'GET':
        return HttpResponseRedirect(reverse('edit-profile'))
    ev = EmailValidation.objects.send(user=request.user)
    return render_to_response('accounts/email_validation_sent.html', {'email':ev.email}, RequestContext(request))

@login_required
def validate_email(request, key):
    (success, fail_reason) = EmailValidation.validate(request.user, key)
    if success:
        return render_to_response('accounts/email_validation_successful.html', {}, RequestContext(request))

    logger.info("email validation failed: %s", fail_reason)
    return render_to_response('accounts/email_validation_failed.html', {'reason':fail_reason}, RequestContext(request))

