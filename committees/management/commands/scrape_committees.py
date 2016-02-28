# encoding: utf-8

from committees.models import Committee
from knesset_data.dataservice.committees import Committee as DataserviceCommittee
from simple.scrapers.management import BaseKnessetDataserviceCommand

_DS_TO_APP_KEY_MAPPING = (
    ('name', 'name'),
    ('knesset_id', 'id'),
    ('knesset_type_id', 'type_id'),
    ('knesset_parent_id', 'parent_id'),
    ('name_eng', 'name_eng'),
    ('name_arb', 'name_arb'),
    ('start_date', 'begin_date'),
    ('end_date', 'end_date'),
    ('knesset_description', 'description'),
    ('knesset_description_eng', 'description_eng'),
    ('knesset_description_arb', 'description_arb'),
    ('knesset_note', 'note'),
    ('knesset_note_eng', 'note_eng'),
    ('knesset_portal_link', 'portal_link')
)


class Command(BaseKnessetDataserviceCommand):
    help = "Fetch the all the committees information from the knesset and update existing"
    _DS_TO_APP_KEY_MAPPING = _DS_TO_APP_KEY_MAPPING

    def _update_or_create(self, fetched_committee):
        """
        If the committee exist merge, and update else create a new entry

        :param fetched_committee: the fetched Committee details
        :return:
        """
        committee = Committee.objects.filter(knesset_id=fetched_committee['knesset_id'])
        if committee:
            self._log_debug(u'Committee {} exist, updating'.format(fetched_committee['name']))
            committee.update(**fetched_committee)
        else:
            self._log_debug(u"Committee {} don't exist, updating".format(fetched_committee['name']))
            Committee.objects.create(**fetched_committee)

    def _update_active_committees(self):
        for ds_committee in DataserviceCommittee.get_all_active_committees(has_portal_link=False):
            committee = dict(self._translate_ds_to_model(ds_committee))
            self._update_or_create(committee)

    def _handle_noargs(self, **options):
        self._update_active_committees()
