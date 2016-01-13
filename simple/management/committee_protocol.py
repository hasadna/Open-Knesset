# -*- coding: utf-8 -*-

import logging, urllib2, re, os

from cStringIO import StringIO
from django.conf import settings
from simple.management.utils import antiword
from pyth.plugins.rtf15.reader import Rtf15Reader

logger = logging.getLogger("open-knesset.syncdata")

DATA_ROOT = getattr(settings, 'DATA_ROOT',
                    os.path.join(settings.PROJECT_ROOT, os.path.pardir, os.path.pardir, 'data'))

ENCODING = 'utf8'


class CommitteProtocolImporter:

    _file = StringIO()
    _directory = os.path.join(DATA_ROOT, 'comm_p')
    _retry_times = 10

    def __init__(self, url):
        self._url = url
        if not os.path.exists(self._directory):
            os.makedirs(self._directory)
        self._file_name = os.path.join(self._directory, 'comm_p.doc')

    def get_text(self):
        logger.debug('get_committee_protocol_text. url=%s' % self._url)
        if self._url.find('html') >= 0:
            self._url = self._url.replace('html','rtf')
        count = 0
        flag = True
        while count < self._retry_times and flag:
            try:
                self._file.write(urllib2.urlopen(self._url).read())
                flag = False
            except Exception:
                count += 1
        if flag:
            logger.error("can't open url %s. tried %d times" % (self._url, count))

        if self._url.find(".rtf") >= 0:
            return self.handle_rtf_protocol()
        if self._url.find(".doc") >= 0:
            return self.handle_doc_protocol()

    def handle_doc_protocol(self):
        directory = os.path.join(DATA_ROOT, 'comm_p')
        f = open(self._file_name, 'wb')
        self._file.seek(0)
        f.write(self._file.read())
        f.close()
        x = antiword(self._file_name)
        x = re.sub('</row>', '\n-------------', x)
        return re.sub('[\n ]{2,}', '\n\n', re.sub('<.*?>','',x))

    def handle_rtf_protocol(self):
        try:
            doc = Rtf15Reader.read(self._file)
        except Exception:
            return ''
        text = []
        attended_list = False
        for paragraph in doc.content:
            for sentence in paragraph.content:
                if 'bold' in sentence.properties and attended_list:
                    attended_list = False
                    text.append('')
                if 'מוזמנים'.decode('utf8') in sentence.content[0] and 'bold' in sentence.properties:
                    attended_list = True
                text.append(sentence.content[0])
        all_text = '\n'.join(text)
        return re.sub(r'\n:\n',r':\n',all_text)