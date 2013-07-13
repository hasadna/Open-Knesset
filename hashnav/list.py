from django.core.paginator import Paginator, InvalidPage
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import smart_str
from base import View

class ListView(View):
    """
    Render some list of objects. This list may be any type via setting
    `self.items`, but if it's a queryset set on `self.queryset` then the
    queryset will be handled correctly.
    """
    def __init__(self, **kwargs):
        self._load_config_values(kwargs, 
            paginate_by = None,
            allow_empty = True,
            template_object_name = 'object',
            queryset = None,
            itemsset = None,
        )
        super(ListView, self).__init__(**kwargs)

    def parse_params(self, *args, **kwargs):
        super(ListView, self).parse_params(*args, **kwargs)

    def get_items(self):
        """
        Get the list of items for this view. This must be an interable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        queryset = self.get_queryset()
        if queryset is not None:
            self.items = queryset
        elif self.itemsset is not None:
            self.items = self.itemsset
        else:
            raise ImproperlyConfigured("'%s' must define 'queryset' or 'items'"
                                        % self.__class__.__name__)

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset._clone()
        else:
            return None

    def get_paginate_by(self):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return self.paginate_by

    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def paginate_items(self):
        """
        Paginate the list of self.items, if needed.
        """
        paginate_by = self.get_paginate_by()
        allow_empty = self.get_allow_empty()
        if not paginate_by:
            if not allow_empty and len(self.items) == 0:
                raise Http404("Empty list and '%s.allow_empty' is False." % self.__class__.__name__)
            self.paginator = None
            self.page = None
            self.items = self.items
        else:
            paginator = Paginator(self.items, paginate_by, allow_empty_first_page=allow_empty)
            # page_descriptor can be either a page number or 'last'
            page_descriptor = getattr(self, 'page', self.request.GET.get('page', 1))
            try:
                page_number = int(page_descriptor)
            except ValueError:
                if page_descriptor == 'last':
                    page_number = paginator.num_pages
                else:
                    raise Http404("Page is not 'last', nor can it be converted to an int.")
            try:
                self.paginator = paginator
                self.page = paginator.page(page_number)
                self.items = self.page.object_list

            except InvalidPage:
                raise Http404('Invalid page (%s)' % page_number)

    def get_template_names(self, suffix='list'):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        names = super(ListView, self).get_template_names()

        # If the list is a queryset, we'll invent a template name based on the
        # app and model name. This name gets put at the end of the template
        # name list so that user-supplied names override the automatically-
        # generated ones.
        if hasattr(self.queryset, 'model'):
            opts = self.queryset.model._meta
            names.append("%s/%s_%s.html" % (opts.app_label, opts.object_name.lower(), suffix))

        return names

    def get_context(self):
        """
        Get the context for this view.
        """
        context = super(ListView, self).get_context()
        self.get_items()
        self.paginate_items()
        template_list_name = '%s_list' % self.template_object_name
        
        params = '' if len(self.request.GET) == 0 else self.request.GET.urlencode() + '&'
        csv_path = 'api/v2' + self.request.path + '?' + params + 'format=csv&limit=0'
        
        context.update({
            'paginator': self.paginator,
            'page_obj': self.page,
            'is_paginated':  self.paginator is not None,
            'csv_path': csv_path,
            template_list_name: self.items,
        })
        return context
