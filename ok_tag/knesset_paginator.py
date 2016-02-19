from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


class SelectorPaginator(Paginator):
    def __init__(self, knesset_ids):
        super(SelectorPaginator, self).__init__(sorted(list(knesset_ids)), 1)

    def validate_number(self, number):
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number not in self.object_list:
            raise EmptyPage('That page contains no result')
        return number

    def page(self, number):
        number = self.validate_number(number)
        return self._get_page([number, ], self.object_list.index(number), self)

    def _get_count(self):
        return len(self.object_list)

    def _get_num_pages(self):
        return len(self.object_list)

    def _get_page_range(self):
        return self.object_list