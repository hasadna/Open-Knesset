# encoding: utf-8

from okscraper.base import BaseScraper
from okscraper.sources import BaseSource
from okscraper.storages import BaseStorage
from events.models import Event
from persons.models import Person
from urlparse import urlparse, parse_qs
from django.conf import settings
from urllib import quote

import urllib2
import json
import dateutil.parser

GOOGLE_CALENDAR_API_KEY = settings.GOOGLE_CALENDAR_API_KEY


class PersonsEventsScraper(BaseScraper):
    """
    runs the MkEventsScraper for each mk with a calendar url
    """

    def __init__(self):
        super(PersonsEventsScraper, self).__init__(self)
        self.source = BaseSource()
        self.storage = BaseStorage()

    def _get_google_cal_page(self, calendar_id, sync_token, page_token=None, is_retry=False):

        if page_token is not None:
            param = '&pageToken=%s' % quote(page_token)
        else:
            param = '&syncToken=%s' % quote(sync_token) if sync_token is not None else ''
        calendar_url = 'https://content.googleapis.com/calendar/v3/calendars/%s/events?showDeleted=true&singleEvents=true%s&key=%s' % (
            quote(calendar_id), param, quote(GOOGLE_CALENDAR_API_KEY))
        try:
            response = urllib2.urlopen(calendar_url)
            data = json.load(response)
            self._getLogger().debug(data)
            res = {}
            res['nextSyncToken'] = data['nextSyncToken'] if 'nextSyncToken' in data else None
            res['nextPageToken'] = data['nextPageToken'] if 'nextPageToken' in data else None
            res['items'] = data['items'] if 'items' in data else []
            return res
        except urllib2.HTTPError as e:
            if e.code == 410 and not is_retry:
                # Retry without sync token according to docs
                self._getLogger().info(u'retrying calendar with sync token invalidated %s' % calendar_id)
                return self._get_google_cal_page(calendar_id=calendar_id, sync_token=None, page_token=page_token,
                                                 is_retry=True)
            self._getLogger().exception(
                u'Exception in trying to fetch google calendar id %s with url %s' % (calendar_id, calendar_url))
            return None

    def _process_items(self, person, items):
        self._getLogger().info('processing %s items' % len(items))
        for item in items:
            status = item.get('status', None)
            icaluid = item.get('iCalUID', None)
            start_date = dateutil.parser.parse(item['start']['dateTime']) if 'start' in item and 'dateTime' in item[
                'start'] else None
            end_date = dateutil.parser.parse(item['end']['dateTime']) if 'end' in item and 'dateTime' in item[
                'end'] else None
            if not all([start_date, end_date, status, icaluid]):
                self._getLogger().error('invalid start / end date / status / iCalUID')
            elif status == 'cancelled':
                res = Event.objects.filter(icaluid=icaluid)
                if res.count() == 1:
                    self._getLogger().info('deleted event')
                    res = res[0]
                    res.cancelled = True
                    res.save()
                else:
                    self._getLogger().info('failed to delete event')
            else:
                # assuming timezone is always israel because I can't seem to save timezone to sqlite
                start_date = start_date.replace(tzinfo=None)
                end_date = end_date.replace(tzinfo=None)
                update_date = dateutil.parser.parse(item['updated']).replace(tzinfo=None) if 'updated' in item else None
                link = item['htmlLink'] if 'htmlLink' in item else None
                summary = item['summary'] if 'summary' in item else None
                description = item['description'] if 'description' in item else None
                # it seems that google never returns the color, although the colorId field is documented
                colorId = item['colorId'] if 'colorId' in item else None
                data = unicode(item)
                kwargs = {
                    'when': start_date, 'when_over': end_date, 'link': link,
                    'what': summary if summary else "",  # what field in DB doesn't allow null value
                    'why': description,  # why field allows null
                    'update_date': update_date,
                }
                event, created = Event.objects.get_or_create(icaluid=icaluid, defaults=kwargs)
                event.who.add(person)
                if created:
                    self._getLogger().info('created new event')
                else:
                    self._getLogger().info('updated event')

    def _scrape(self):
        for person in Person.objects.filter(calendar_url__isnull=False).distinct():
            qs = parse_qs(urlparse(person.calendar_url).query)
            self._getLogger().info('processing person %s' % person.id)
            if 'src' not in qs:
                self._getLogger().warn('invalid calendar url for person %s: %s' % (person.id, person.calendar_url))
            else:
                calendar_id = qs['src'][0]
                self._getLogger().debug('processing calendar_id: %s' % calendar_id)
                res = self._get_google_cal_page(calendar_id, person.calendar_sync_token)
                if res:
                    self._process_items(person, res['items'])
                    while res['nextPageToken'] is not None:
                        self._getLogger().debug('processing next page..')
                        res = self._get_google_cal_page(calendar_id, None, res['nextPageToken'])
                        self._process_items(person, res['items'])
                    if res['nextSyncToken'] is None:
                        self._getLogger().error('did not get nextToken!')
                    else:
                        person.calendar_sync_token = res['nextSyncToken']
                        person.save()
