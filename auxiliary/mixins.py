import csv
import json

from django.http import HttpResponse, Http404
from django.views.generic import ListView
from django.views.generic.list import BaseListView


class GetMoreView(ListView):
    """A base view for feeding data to 'get more...' type of links

    Will return a json result, with partial of rendered template:
    {
        "content": "....",
        "current": current_page number
        "total": total_pages
        "has_next": true if next page exists
    }
    We'll paginate the response. Since Get More link targets may already have
    initial data, we'll look for `initial` GET param, and take it into
    consideration, completing to page size.
    """

    def get_context_data(self, **kwargs):
        ctx = super(GetMoreView, self).get_context_data(**kwargs)
        try:
            initial = int(self.request.GET.get('initial', '0'))
        except ValueError:
            initial = 0

        # initial only affects on first page
        if ctx['page_obj'].number > 1 or initial >= self.paginate_by - 1:
            initial = 0

        ctx['object_list'] = ctx['object_list'][initial:]
        return ctx

    def render_to_response(self, context, **response_kwargs):
        """We'll take the rendered content, and shove it into json"""

        tmpl_response = super(GetMoreView, self).render_to_response(
            context, **response_kwargs).render()

        page = context['page_obj']

        result = {
            'content': tmpl_response.content,
            'total': context['paginator'].num_pages,
            'current': page.number,
            'has_next': page.has_next(),
        }

        return HttpResponse(json.dumps(result, ensure_ascii=False),
                            content_type='application/json')


class CsvView(BaseListView):
    """A view which generates CSV files with information for a model queryset.
    Important class members to set when inheriting:
      * model -- the model to display information from.
      * queryset -- the query performed on the model; defaults to all.
      * filename -- the name of the resulting CSV file (e.g., "info.csv").
      * list_display - a list (or tuple) of tuples, where the first item in
        each tuple is the attribute (or the method) to display and
        the second item is the title of that column.

        The attribute can be a attribute on the CsvView child or the model
        instance itself. If it's a callable it'll be called with (obj, attr)
        for the CsvView attribute or without params for the model attribute.
    """

    filename = None
    list_display = None

    def dispatch(self, request):
        if None in (self.filename, self.list_display, self.model):
            raise Http404()
        self.request = request
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = \
            'attachment; filename="{}"'.format(self.filename)

        object_list = self.get_queryset()
        self.prepare_csv_for_utf8(response)
        writer = csv.writer(response, dialect='excel')
        writer.writerow([title.encode('utf8')
                         for _, title in self.list_display])
        for obj in object_list:
            row = [self.get_display_attr(obj, attr)
                   for attr, _ in self.list_display]
            writer.writerow([unicode(item).encode('utf8') for item in row])
        return response

    def get_display_attr(self, obj, attr):
        """Return the display string for an attr, calling it if necessary."""
        display_attr = getattr(self, attr, None)
        if display_attr is not None:
            if callable(display_attr):
                display_attr = display_attr(obj, attr)
        else:
            display_attr = getattr(obj, attr)
            if callable(display_attr):
                display_attr = display_attr()
        if display_attr is None:
            return ""
        return display_attr

    @staticmethod
    def prepare_csv_for_utf8(fileobj):
        """Prepend a byte order mark (BOM) to a file.

        When Excel opens a CSV file, it assumes the encoding is ASCII. The BOM
        directs it to decode the file with utf-8.
        """
        fileobj.write('\xef\xbb\xbf')