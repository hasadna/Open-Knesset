# Django settings for knesset project.
import os
import logging

# dummy gettext, to get django-admin makemessages to find i18n texts in this file
gettext = lambda x: x

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'dev.db',
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Asia/Jerusalem'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'he'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

PROJECT_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    os.path.pardir
))

DATA_ROOT = os.path.join(PROJECT_ROOT, 'data', '')

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media', '')

# Absolute path to location of collected static files
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static_root', '')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '1_ovxxkf(c*z_dwv!(-=dezf#%l(po5%#zzi*su-$d*_j*1sr+'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
    # 'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  # keep after session
    'django.middleware.csrf.CsrfViewMiddleware',
    'pagination.middleware.PaginationMiddleware',
    # make sure to keep the DebugToolbarMiddleware last
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'social_auth.backends.twitter.TwitterBackend',
    'social_auth.backends.facebook.FacebookBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
    'social_auth.backends.google.GoogleBackend',
    'social_auth.backends.contrib.github.GithubBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_CREATE_USERS = True
SOCIAL_AUTH_FORCE_RANDOM_USERNAME = False
SOCIAL_AUTH_ASSOCIATE_BY_MAIL = True
# These keys will work for 127.0.0.1:8000
# and are overriden in the production server.
TWITTER_CONSUMER_KEY = 'KFZkQgImAyECXDS6tQTvOw'
TWITTER_CONSUMER_SECRET = 's6ir2FMqw4fqXQbX4QCE6Ka1lRjycXxJuG6k8tYc'

ROOT_URLCONF = 'knesset.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),  # Finding current static files
)

LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, 'locale'),
)
INSTALLED_APPS = (
    'django.contrib.auth',          # django apps
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.sitemaps',
    'django.contrib.flatpages',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'piston',                       # friends apps
    'debug_toolbar',
    'tagging',
    'south',
    'planet',
    'pagination',
    'django_extensions',
    'actstream',
    'avatar',
    'hitcount',
    'annotatetext',
    'mailer',
    'backlinks',
    'backlinks.pingback',
    'backlinks.trackback',
    'django_nose',
    'gunicorn',
    'djangoratings',
    'voting',
    'social_auth',
    'devserver',
    #'knesset',
    'auxiliary',                  # knesset apps
    'mks',
    'mmm',
    'laws',
    'committees',
    'simple',
    'tagvotes',
    'accounts',
    'links',
    'user',
    'agendas',
    'badges',
    'notify',
    'persons',
    'events',
    'video',
    'okhelptexts',
    'tastypie',
    'polyorg',
    'plenum',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "knesset.context.processor",
    "social_auth.context_processors.social_auth_by_name_backends",
    "social_auth.context_processors.social_auth_backends",
)
INTERNAL_IPS = ()
# Add the following line to your local_settings.py files to enable django-debug-toolar:
#INTERNAL_IPS = ('127.0.0.1',)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

LOCAL_DEV = True

LOGIN_URL = '/users/login/'

SITE_NAME = 'Open-Knesset'

MAX_TAG_LENGTH = 128

AUTH_PROFILE_MODULE = 'user.UserProfile'

LOGIN_REDIRECT_URL = '/'

USER_AGENT = "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)"

LOG_FILENAME = os.path.join(PROJECT_ROOT, 'open-knesset.log')
logger = logging.getLogger("open-knesset")
logger.setLevel(logging.DEBUG)  # override this in prod server to logging.ERROR
h = logging.FileHandler(LOG_FILENAME)
h.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s\t%(name)s:%(lineno)d\t%(levelname)s\t%(message)s")
h.setFormatter(formatter)
logger.addHandler(h)

GOOGLE_CUSTOM_SEARCH = "011858809565220576533:pyrgq6kc_cy"
GOOGLE_MAPS_API_KEYS = {'dev': 'ABQIAAAAWCfW8hHVwzZc12qTG0qLEhQCULP4XOMyhPd8d_NrQQEO8sT8XBQdS2fOURLgU1OkrUWJE1ji1lJ-3w',
                        'prod': 'ABQIAAAAWCfW8hHVwzZc12qTG0qLEhR8lgcBs8YFes75W3FA_wpyzLVCpRTF-eaJoRuCHAJ2qzVu-Arahwp8QA'}
GOOGLE_MAPS_API_KEY = GOOGLE_MAPS_API_KEYS['dev']  # override this in prod server

# you need to generate a token and put it in local_settings.py
# to generate a token run: bin/django update_videos --get-youtube-token
YOUTUBE_AUTHSUB_TOKEN = ''

# you need to get a developer key and put it in local_settings.py
# to get a developer key goto: http://code.google.com/apis/youtube/dashboard
YOUTUBE_DEVELOPER_KEY = ''

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

LONG_CACHE_TIME = 18000  # 5 hours

ANNOTATETEXT_FLAGS = (
    gettext('Statement'),
    gettext('Funny :-)'),
    gettext('False fact'),
    gettext('Source?'),
    gettext('Found source'),
    gettext('Cross reference'),
    gettext('Important'),
    gettext('Formatting/Error!'),
    gettext('Comment'),
)

AUTO_GENERATE_AVATAR_SIZES = (75, 48)

HITCOUNT_KEEP_HIT_ACTIVE = {'hours': 1}
HITCOUNT_HITS_PER_IP_LIMIT = 0
HITCOUNT_EXCLUDE_USER_GROUP = ()

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['--with-xunit']


SERIALIZATION_MODULES = {
    'oknesset': 'auxiliary.serializers'
}

API_LIMIT_PER_PAGE = 1000

SOUTH_TESTS_MIGRATE = False

# if you add a local_settings.py file, it will override settings here
# but please, don't commit it to git.
try:
    from local_settings import *
except ImportError:
    pass
