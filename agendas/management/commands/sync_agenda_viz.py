import os
from cStringIO import StringIO

import shutil
import urllib2
from django.conf import settings
from django.core.management.base import NoArgsCommand
from zipfile import ZipFile


class Command(NoArgsCommand):

    help = "Sync ok-agenda-wiz media from ydaniv's repo"
    ZIP_URL = 'https://github.com/ydaniv/ok-agenda-viz/archive/master.zip'
    _static_root = settings.STATICFILES_DIRS[0]
    _templates_root = settings.TEMPLATE_DIRS[0]

    _DIRS = {
        'dist': os.path.join(_static_root, 'js'),
        'css': os.path.join(_static_root, 'css'),
        'img': os.path.join(_static_root, 'img', 'agenda-viz'),
    }
    _html_file = 'agenda-widget.html'

    _replacements = (
        ('/lib/require.js', '{% static "js/require.js" %}'),
        ('src/agenda-viz.js', '{{% static "js/{0}" %}}'),
        ('/src/css/openfont.css', '{% static "css/openfont.css" %}'),
        ('/src/img/', '{% static "img/agenda-viz/" %}'),
        ('</body>', '    <script>window.IMAGES_PATH = "{% static "img/agenda-viz/" %}";</script>\n</body>'),
    )

    def handle_noargs(self, **options):

        is_verbose = options['verbosity'] > 0

        if is_verbose:
            print "Syncing into", self._static_root
            print "Getting zip from ", self.ZIP_URL

        zip_url = urllib2.urlopen(self.ZIP_URL)
        zip_file = ZipFile(StringIO(zip_url.read()))

        content = None
        js_with_version = None

        for member in zip_file.namelist():
            # we take only dist, css, and img directories
            dir_name, file_name = os.path.split(member)

            # skip directories
            if not file_name:
                continue

            _, base_dir = os.path.split(dir_name)

            if file_name == self._html_file:
                with zip_file.open(member) as source:
                    content = source.read()

            if base_dir == 'dist':
                js_with_version = file_name

            elif base_dir in self._DIRS:
                target_dir = self._DIRS[base_dir]
                if is_verbose:
                    print "Copying {0} to {1}".format(member, target_dir)

                # make sure we have the target_dir dir
                try:
                    os.makedirs(target_dir)
                except OSError:
                    pass

                with zip_file.open(member) as source,  \
                    file(os.path.join(target_dir, file_name), "wb") as target: 
                    shutil.copyfileobj(source, target)

        if is_verbose:
            print "Adopting ", self._html_file

        # now adopt the template content, with the found version number
        content = "{% load static from staticfiles %}\n" + content

        for orig, replacement in self._replacements:
            if replacement.find('{0}') > -1:
                replacement = replacement.format(js_with_version)
            content = content.replace(orig, replacement)

        target = os.path.join(self._templates_root, 'agendas', self._html_file)

        with open(target, 'w') as f:
            f.write(content)
