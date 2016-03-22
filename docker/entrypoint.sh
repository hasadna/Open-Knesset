#!/bin/sh

cp docker/docker_settings.py knesset/local_settings.py && \
python manage.py migrate && \
python manage.py createsuperuser --noinput --username=superuser --email=superuser@example.com && \
$*
