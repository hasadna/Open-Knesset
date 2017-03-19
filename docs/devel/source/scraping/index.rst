========
Scraping
========

One of the most important tasks in Open Knesset are the scraping processes, this document will try to describe all those processes (but pay attention that as the code changes, this documentation might not..)

We are currently moving towards having knesset-data-django project handle all the scraping jobs.

See the project documentation for more details: https://github.com/hasadna/knesset-data-django/blob/master/README.md

Knesset-data-django is integrated in Open Knesset, so you can run the management commands detailed there in Open Knesset.

Scraping Tasks
==============

.. toctree::
    :maxdepth: 2

    votes
    committees
    presence

Where and how the tasks are run
===============================

The scraping tasks are all run from the db server using cron, these are the cron jobs (last updated: ~2015):

.. code-block:: sh

    1 02,14 * * * /oknesset_data/oknesset/Open-Knesset/manage.py update_all_feeds
    05 06,12,18 * * * /oknesset_data/presence/PresenceChecker.sh
    30 03 * * * /oknesset_data/oknesset/Open-Knesset/manage.py update_videos --only-members --current-knesset
    45 03 * * * /oknesset_data/oknesset/Open-Knesset/manage.py parse_plenum_protocols --download --parse
    00 04 * * * /oknesset_data/oknesset/Open-Knesset/manage.py parse_future_plenum_meetings
    15 04 * * * /oknesset_data/oknesset/Open-Knesset/manage.py syncdata --update
    59 04 * * * /oknesset_data/oknesset/Open-Knesset/manage.py send_email_to_editors
    00 05 * * * /oknesset_data/oknesset/Open-Knesset/manage.py notify --daily
    01 05 * * 5 /oknesset_data/oknesset/Open-Knesset/manage.py notify --weekly
    02 01,05,09,13,17,21 * * * /oknesset_data/oknesset/Open-Knesset/manage.py send_mail
    03 05 * * * /oknesset_data/oknesset/Open-Knesset/manage.py parse_future_committee_meetings
    30 04 * * * /oknesset_data/oknesset/Open-Knesset/manage.py okscrape lobbyists --dblog
