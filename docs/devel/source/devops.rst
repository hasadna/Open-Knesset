==========================================
DevOps - Servers, Configuration, Deployment, Common tasks
==========================================

Servers
============================

Following is the servers configuration (as it was on Feb. 16, 2016):
 
db1
  DB server, runs cronjobs, (EC2 Name: Postgres1)

small1
  web app

small2
  web app

Configuration
=============

You can find some configuration files in https://github.com/hasadna/Open-Knesset/blob/master/deploy/

web app servers
  Runs supervisor service which includes oknesset app
  
  The file /etc/supervisor/conf.d/oknesset.conf contains the relevant configuration
  
  This is the command that it runs: command=newrelic-admin run-program gunicorn knesset.wsgi:application -w 4 -t 60

db servers
  Runs the DB
  Runs cronjobs, see https://github.com/hasadna/Open-Knesset/blob/master/deploy/crontab.txt

Deployment
==========

Deployment is done using fabric, see: https://github.com/hasadna/Open-Knesset/blob/master/fabfile.py

There is a local_fab_settings.py file which contains login details.

common deployment tasks
-----------------------

$ fab deploy_backend
  deploy to the db server

$ fab deploy_backend:migration=yes
  deploy to db and run ./manage.py migrate as well
  
$ fab deploy_backend:requirements=yes,migration=yes
  deploy to db, run migrations and also pip install -r requirements.txt
  
$ fab deploy_web
  deploy to the web servers (small1, small2)

$ fab deploy_web:requirements=yes
  deploy to the web servers and also run pip install -r requirements.txt
