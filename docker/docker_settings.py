"""Extension and overloading for running in docker."""
import logging
import sys


DATABASES = {
    'default': {
        'NAME': '/opt/database/dev.db',
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

logger = logging.getLogger("open-knesset")
logger.handlers = []
logger.setLevel(logging.DEBUG)  # override this in prod server to logging.ERROR
h = logging.StreamHandler(sys.stdout)
h.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s\t%(name)s:%(lineno)d\t%(levelname)s\t%(message)s")
h.setFormatter(formatter)
logger.addHandler(h)
