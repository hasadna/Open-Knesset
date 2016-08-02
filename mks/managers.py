import difflib
from django.core.cache import cache
from django.db import models, connection
from django.db.models import Q

# from agendas.models import Agenda


class KnessetManager(models.Manager):
    """This is a manager for Knesset class"""

    def __init__(self):
        super(KnessetManager, self).__init__()
        self._current_knesset = None

    def current_knesset(self):
        if self._current_knesset is None:
            try:
                self._current_knesset = self.get_query_set().order_by('-number')[0]
            except IndexError:
                # FIX: should document when and why this should happen
                return None
        return self._current_knesset


class BetterManager(models.Manager):
    def __init__(self):
        super(BetterManager, self).__init__()
        self._names = []

    def find(self, name):
        ''' looks for a member with a name that resembles 'name'
            the returned array is ordered by similiarity
        '''
        names = cache.get('%s_names' % self.model.__name__)
        if not names:
            names = self.values_list('name', flat=True)
            cache.set('%s_names' % self.model.__name__, names)
        possible_names = difflib.get_close_matches(
            name, names, cutoff=0.5, n=5)
        qs = self.filter(name__in=possible_names)
        # used to establish size, overwritten later
        ret = range(qs.count())
        for m in qs:
            if m.name == name:
                return [m]
            ret[possible_names.index(m.name)] = m
        return ret


class PartyManager(BetterManager):
    def parties_during_range(self, ranges=None):
        from agendas.models import Agenda
        filters_folded = Agenda.generateSummaryFilters(ranges, 'start_date', 'end_date')
        return self.filter(filters_folded)


class CurrentKnessetPartyManager(models.Manager):
    def __init__(self):
        super(CurrentKnessetPartyManager, self).__init__()
        self._current = None

    def get_query_set(self):
        # caching won't help here, as the query set will be re-run on each
        # request, and we may need to further run queries down the road
        from mks.models import Knesset
        qs = super(CurrentKnessetPartyManager, self).get_query_set()
        qs = qs.filter(knesset=Knesset.objects.current_knesset())
        return qs

    @property
    def current_parties(self):
        if self._current is None:
            self._current = list(self.get_query_set())

        return self._current


class CurrentKnessetMembersManager(models.Manager):
    "Adds the ability to filter on current knesset"

    def get_queryset(self):
        from mks.models import Knesset
        qs = super(CurrentKnessetMembersManager, self).get_queryset()
        # TODO: Strange? why should we filter by knesset and not other options?
        current_knesset = Knesset.objects.current_knesset()
        qs = qs.filter(current_party__knesset=current_knesset)
        return qs


class MembershipManager(models.Manager):
    def membership_in_range(self, ranges=None, only_current_mks=False):
        if only_current_mks:
            from mks.models import Knesset, Membership
            return Membership.objects.filter(member__is_current=True).values_list('member_id', flat=True)
        elif not ranges:
            return
        else:
            filter_list = []
            query_parameters = []
            for r in ranges:
                if not r[0] and not r[1]:
                    return None  # might as well not filter at all
                query_fields = []
                query_parameters = []
                if r[0]:
                    query_fields.append("coalesce(end_date, '2037-01-01') < %s")
                    query_parameters.append(r[0])
                if r[1]:
                    query_fields.append("coalesce(start_date, '1947-01-01') >= %s")
                    query_parameters.append(r[1])
                filter_list.append(' OR '.join(query_fields))

            filters_folded = ' AND '.join(filter_list)
            query = "SELECT member_id FROM mks_membership WHERE NOT (%s)" % filters_folded
            cursor = connection.cursor()
            cursor.execute(query, query_parameters)
            results = cursor.fetchall()
            return [c[0] for c in results]
