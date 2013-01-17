from django.utils.encoding import smart_text
from django.db.models import Q, Manager

class PersonManager(Manager):

    def get_by_name(self, name):
        name = smart_text(name)
        return self.get((Q(aliases__name__in=name) | Q(name=name)))

