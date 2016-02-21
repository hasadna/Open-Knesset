import json
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.db import models
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin

from .models import Suggestion
from auxiliary.decorators import login_required_ajax
from auxiliary.serializers import PromiseAwareJSONEncoder


class PendingSuggestionsCountView(View):
    """Return the pending suggestions for Model/Instance.

    The view can return the results for multiple models/objects. Pass each in
    the query string's ``for`` argument, e.g::

        ?for=auxiliary.Tidbit&for=events.Event&for=mks.Member-801

    The last one in the example above get's pending for Member instance with
    pk=801.
    """

    def get_models_and_instances(self, request):
        "Returns models/instances in GET param ``for``"

        items = request.GET.getlist('for')
        for item in items:
            try:
                model_name, pk = item.split('-', 1)
            except ValueError:
                model_name, pk = item, None

            model = models.get_model(*model_name.split('.', 1))

            if pk is None:
                yield model
            else:
                instance = model.objects.get(pk=pk)
                yield instance

    def get_pending(self, request):
        res = {}

        for model_or_instance in self.get_models_and_instances(request):
            if isinstance(model_or_instance, models.Model):
                key = unicode(model_or_instance)
            else:
                key = unicode(model_or_instance._meta.verbose_name)

            res[key] = Suggestion.objects.get_pending_suggestions_for(
                model_or_instance)

        return res

    def prepare_pending(self, result, can_apply=False):
        "Prepares the QuerySet for the response"

        res = {}

        for key in result:
            count = result[key].count()
            if count:
                res[key] = count

        return res

    def get(self, request, *args, **kwargs):
        res = self.get_pending(request)
        can_apply = request.user.has_perm('suggestions.autoapply_suggestion')
        res = self.prepare_pending(res, can_apply=can_apply)

        return HttpResponse(
            json.dumps(res, ensure_ascii=False, cls=PromiseAwareJSONEncoder),
            mimetype='application/json')


class PendingSuggestionsView(PendingSuggestionsCountView):

    def prepare_pending(self, result, can_apply=False):
        "Prepares the QuerySet for the response"

        for key in result:
            result[key] = [
                {
                    'label': unicode(x),
                    'apply_url': can_apply and x.can_auto_apply and reverse(
                        'suggestions_auto_apply', kwargs={'pk': x.pk}),
                    'reject_url': can_apply and reverse(
                        'suggestions_reject', kwargs={'pk': x.pk}),
                    'by': unicode(x.suggested_by),
                    'by_url': x.suggested_by.profiles.get().get_absolute_url(),
                    'by_email': can_apply and x.suggested_by.email,
                    'suggested_at': x.suggested_at.strftime('%Y-%m-%d %H:%M'),
                }
                for x in result[key]]

        return result

    @method_decorator(login_required_ajax)
    def get(self, request, *args, **kwargs):
        return super(PendingSuggestionsView, self).get(
            request, *args, **kwargs)


class AutoApplySuggestionView(SingleObjectMixin, View):
    "Auto apply a suggestion"

    model = Suggestion

    @method_decorator(permission_required('suggesions.autoapply_suggestion',
                                          raise_exception=True))
    def post(self, request, *args, **kwargs):
        suggestion = self.get_object()

        if not suggestion.can_auto_apply:
            res = {
                'success': False,
                'message': "Can't auto apply this suggestion"
            }
        else:
            suggestion.auto_apply(request.user)
            res = {
                'success': True,
            }

        return HttpResponse(
            json.dumps(res, ensure_ascii=False, cls=PromiseAwareJSONEncoder),
            mimetype='application/json')


class RejectSuggestionView(SingleObjectMixin, View):
    "Reject a suggestion"

    model = Suggestion

    @method_decorator(permission_required('suggesions.autoapply_suggestion',
                                          raise_exception=True))
    def post(self, request, *args, **kwargs):
        suggestion = self.get_object()
        reason = request.POST.get('reason', 'Unknown')

        suggestion.reject(request.user, reason)
        res = {
            'success': True,
        }

        return HttpResponse(
            json.dumps(res, ensure_ascii=False, cls=PromiseAwareJSONEncoder),
            mimetype='application/json')
