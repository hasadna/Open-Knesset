# Create your views here.

from datetime import datetime

import vobject

from django.http import HttpResponse
from hashnav.detail import DetailView
from models import Event

class EventDetailView(DetailView):
    model = Event
    def get_context_data(self, *args, **kwargs):
        context = super(EventDetailView, self).get_context_data(**kwargs)
        context['creators'] = [x.mk for x in context['object'].who.all()]
        return context

def icalendar(request, summary_length=50, future_only=True):
    """
    return a single icalendar file, default to future_only.
    """
    summary_length = int(summary_length)
    cal = vobject.iCalendar()
    now = datetime.now()
    for e in Event.objects.all():
        # TODO - use a proper query once I recall the syntax (actually the
        # implementation of is_future makes this query pretty bad, since it
        # will execute multiple times - to do this properly I need some sort of
        # select * from table where start_date > $now, then now is only
        # calculated once, and this should be log(N) time (assuming an ordered
        # index on start_date)
        if future_only and e.when <= now:
            continue
        e.add_vevent_to_ical(cal, summary_length=summary_length)
    return HttpResponse(cal.serialize())
