from StringIO import StringIO
from urllib2 import HTTPError, URLError
from backlinks.pingback.server import default_server

from django.core.handlers.wsgi import STATUS_CODE_TEXT

PINGABLE_MEMBER_ID = '1'
NON_PINGABLE_MEMBER_ID = '2'

# Mock URL reader utilities

class Headers(object):
    def __init__(self, headers_dict):
        self._headers = self.build_headers(headers_dict)

    def build_headers(self, headers_dict):
        built = {}
        for key, value in headers_dict.items():
            built[key.lower()] = value
        return built

    def getheader(self, name, default=None):
        return self._headers.get(name.lower(), default)

    get = getheader

class MockResponseWrapper(object):
    def __init__(self, url, content, headers):
        self.url = url
        self.fp = content
        self._read = self.fp.read
        self.headers = Headers(headers)
        self._body = ''
        self.charset = 'utf-8'

    def read(self, max_length=None):
        c = self._read(max_length)
        self._body = self._body + c
        return c
    
    def get_body(self):
        if not self._body:
            self.read()
        return self._body

    body = property(get_body)


class MockReader(object):
    headers = {'Content-Type': 'text/html; charset=utf-8'}

    def __init__(self, url_mappings=None, headers=None):
        self.url_mappings = url_mappings or {}
        self.headers = headers or self.headers

    def open(self, url):
        try:
            content, headers_dict = self.url_mappings[url]
        except KeyError:
            raise IOError # simulate a connection error
        if callable(content):
            content = content()
        if not hasattr(content, 'read'):
            f = StringIO(content)
        headers = self.headers
        if not headers_dict and headers_dict != {}:
            headers_dict = {}
        headers.update(headers_dict)
        return MockResponseWrapper(url, f, headers)

# Mock sources

def raise_http_error(url, code):
    raise HTTPError(url, code, STATUS_CODE_TEXT.get(code, ''), None, None)

def raise_url_error():
    raise URLError


HTML_TEMPLATE = '<html><head><title>%(title)s</title></head><body><h1>%(title)s</h1><p>%(content)s</p></body></html>'


LINKING_SOURCE = HTML_TEMPLATE % {'title': 'Test Pingback Good Source Document',
                                  'content': 'This is a test document which <a href="http://example.com/member/'+PINGABLE_MEMBER_ID+'/mk_'+PINGABLE_MEMBER_ID+'/">links to</a> a known pingable resource. And <a href="http://example.com/member/'+PINGABLE_MEMBER_ID+'/">another</a>'}

NON_LINKING_SOURCE = HTML_TEMPLATE % {'title': 'Test Pingback Bad Source Document',
                                      'content': 'This is a test document which does not link to a known pingable resource.'}

url_mappings = {
    'http://example.com/non-existent-resource/': (lambda: raise_http_error('http://example.com/non-existent-resource/', 404), {}),
    'http://example.com/server-error/': (lambda: raise_http_error('http://example.com/server-error/', 500), None),
    'http://example.com/good-source-document/': (LINKING_SOURCE, None),
    'http://example.com/bad-source-document/': (NON_LINKING_SOURCE, None),
    'http://example.com/another-good-source-document/': (LINKING_SOURCE, None),
}

mock_reader = MockReader(url_mappings=url_mappings)
default_server.url_reader = mock_reader
# Mock targets





