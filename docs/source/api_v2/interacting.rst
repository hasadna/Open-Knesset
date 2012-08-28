.. _ref-interacting:

========================
Interacting With The API
========================

.. tip::
    Version 2 of the API  is served using `django-tastypie`_. This section is mostly
    a verbatim copy of their `interacting page`_.

.. _interacting page: http://django-tastypie.readthedocs.org/en/latest/interacting.html
.. _django-tastypie: https://github.com/toastdriven/django-tastypie


We'll assume that you have cURL_ installed on your system (generally available
on most modern Mac & Linux machines), but any tool that allows you to control
headers & bodies on requests will do.

.. _cURL: http://curl.haxx.se/

Let's fire up a shell & start exploring the API!

Front Matter
============

Tastypie tries to treat all clients & all serialization types as equally as
possible. It also tries to be a good 'Net citizen & respects the HTTP method
used as well as the ``Accepts`` headers sent. Between these two, you control
all interactions with Tastypie through relatively few endpoints.

.. warning::

  Should you try these URLs in your browser, be warned you **WILL** need to
  append ``?format=json`` (or ``xml`` or ``yaml``) to the URL. Your browser
  requests ``application/xml`` before ``application/json``, so you'll always
  get back XML if you don't specify it.

  That's also why it's recommended that you explore via curl, because you
  avoid your browser's opinionated requests & get something closer to what
  any programmatic clients will get.


Fetching Data
=============

Since reading data out of an API is a very common activity (and the easiest
type of request to make), we'll start there. Tastypie tries to expose various
parts of the API & interlink things within the API (HATEOAS).

Api-Wide
--------

We'll start at the highest level::

    curl http://oknesset.org/api/v2/

You'll get back something like::

    {
        "agenda": {
            "list_endpoint": "/api/v2/agenda/",
            "schema": "/api/v2/agenda/schema/"
        },
        "agenda-todo": {
            "list_endpoint": "/api/v2/agenda-todo/",
            "schema": "/api/v2/agenda-todo/schema/"
        },
        "bill": {
            "list_endpoint": "/api/v2/bill/",
            "schema": "/api/v2/bill/schema/"
        },
        "law": {
            "list_endpoint": "/api/v2/law/",
            "schema": "/api/v2/law/schema/"
        },
        "link": {
            "list_endpoint": "/api/v2/link/",
            "schema": "/api/v2/link/schema/"
        },
        "member": {
            "list_endpoint": "/api/v2/member/",
            "schema": "/api/v2/member/schema/"
        },
        "member-agendas": {
            "list_endpoint": "/api/v2/member-agendas/",
            "schema": "/api/v2/member-agendas/schema/"
        },
        "member-bills": {
            "list_endpoint": "/api/v2/member-bills/",
            "schema": "/api/v2/member-bills/schema/"
        },
        "party": {
            "list_endpoint": "/api/v2/party/",
            "schema": "/api/v2/party/schema/"
        },
        "video": {
            "list_endpoint": "/api/v2/video/",
            "schema": "/api/v2/video/schema/"
        }

    }

This lists out all the different resources provided by the API. 
Each one is listed by the resource name and provides the ``list_endpoint`` & the
``schema`` for the resource.

Note that these links try to direct you to other parts of the API, to make
exploration/discovery easier. We'll use these URLs in the next several
sections.


.. _schema-inspection:

Inspecting The Resource's Schema
--------------------------------

Since the api-wide view gave us a ``schema`` URL, let's inspect that next.
We'll use the ``member`` resource. Again, a simple GET request by curl::

    curl http://oknesset.org/api/v2/member/schema/

This time, we get back a lot more data (snipped for clarity)::

    {

        "allowed_detail_http_methods": [
            "get"
        ],
        "allowed_list_http_methods": [
            "get"
        ],
        "default_format": "application/json",
        "default_limit": 1000,
        "fields": {
            "agendas_uri": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Unicode string data. Ex: \"Hello World\"",
                "nullable": false,
                "readonly": false,
                "type": "string",
                "unique": false
            },
            "average_monthly_committee_presence": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Floating point numeric data. Ex: 26.73",
                "nullable": true,
                "readonly": false,
                "type": "float",
                "unique": false
            },
            "average_weekly_presence_hours": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Floating point numeric data. Ex: 26.73",
                "nullable": true,
                "readonly": false,
                "type": "float",
                "unique": false
            },
            "bills_stats_approved": {
                "blank": false,
                "default": 0,
                "help_text": "Integer data. Ex: 2673",
                "nullable": false,
                "readonly": false,
                "type": "integer",
                "unique": false
            },
            "bills_stats_first": {
                "blank": false,
                "default": 0,
                "help_text": "Integer data. Ex: 2673",
                "nullable": false,
                "readonly": false,
                "type": "integer",
                "unique": false
            },
            "is_current": {
                "blank": true,
                "default": true,
                "help_text": "Boolean data. Ex: True",
                "nullable": false,
                "readonly": false,
                "type": "boolean",
                "unique": false
            },
            "name": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Unicode string data. Ex: \"Hello World\"",
                "nullable": false,
                "readonly": false,
                "type": "string",
                "unique": false
            },
            "number_of_children": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Integer data. Ex: 2673",
                "nullable": true,
                "readonly": false,
                "type": "integer",
                "unique": false
            },
            "party_name": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Unicode string data. Ex: \"Hello World\"",
                "nullable": false,
                "readonly": false,
                "type": "string",
                "unique": false
            },
            "party_url": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Unicode string data. Ex: \"Hello World\"",
                "nullable": false,
                "readonly": false,
                "type": "string",
                "unique": false
            },
            "year_of_aliyah": {
                "blank": false,
                "default": "No default provided.",
                "help_text": "Integer data. Ex: 2673",
                "nullable": true,
                "readonly": false,
                "type": "integer",
                "unique": false
            }
        },
        "filtering": {
            "is_current": 1,
            "name": 1
        },
        "ordering": [
            "name",
            "is_current",
            "bills_stats_proposed",
            "bills_stats_pre",
            "bills_stats_first",
            "bills_stats_approved"
        ]

    }


This lists out the ``default_format`` this resource responds with, the
``fields`` on the resource & the ``filtering`` options available. This
information can be used to prepare the other aspects of the code for the
data it can obtain & ways to filter the resources.


Getting A Collection Of Resources
---------------------------------

Let's get down to fetching live data. From the api-wide view, we'll hit
the ``list_endpoint`` for ``member``::

    curl http://oknesset.org/api/v2/member/

We get back data that looks like (lot of objects snipped for clarity)::

    {

        "meta": {
            "limit": 1000,
            "next": null,
            "offset": 0,
            "previous": null,
            "total_count": 128
        },
        "objects": [
            {
                "agendas_uri": "/api/v2/member-agendas/214/",
                "average_monthly_committee_presence": 0.16,
                "average_weekly_presence_hours": 6.1,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 0,
                "bills_stats_proposed": 3,
                "bills_uri": "/api/v2/bill/?proposer=214",
                "current_role_descriptions": "סגן ראש הממשלה, שר החוץ",
                "date_of_birth": "1958-06-05",
                "date_of_death": null,
                "email": "aliberman@knesset.gov.il",
                "end_date": null,
                "family_status": "נשוי",
                "fax": "02-6408921",
                "gender": "זכר",
                "id": 214,
                "img_url": "http://www.knesset.gov.il/mk/images/members/liberman_avigdor-s.jpg",
                "is_current": true,
                "name": "אביגדור ליברמן",
                "number_of_children": 3,
                "party_name": "ישראל ביתנו",
                "party_url": "/party/5/%D7%99%D7%A9%D7%A8%D7%90%D7%9C-%D7%91%D7%99%D7%AA%D7%A0%D7%95/",
                "phone": "02-6408388",
                "place_of_birth": "ברה”מ, ברית המועצות",
                "place_of_residence": "נוקדים",
                "place_of_residence_lat": "31.64533",
                "place_of_residence_lon": "35.244065",
                "residence_centrality": 5,
                "residence_economy": 4,
                "resource_uri": "/api/v2/member/214/",
                "start_date": "2009-02-24",
                "year_of_aliyah": 1978
            },
            {
                "agendas_uri": "/api/v2/member-agendas/771/",
                "average_monthly_committee_presence": 0.24,
                "average_weekly_presence_hours": 16,
                "bills_stats_approved": 1,
                "bills_stats_first": 1,
                "bills_stats_pre": 3,
                "bills_stats_proposed": 17,
                "bills_uri": "/api/v2/bill/?proposer=771",
                "current_role_descriptions": null,
                "date_of_birth": "1952-12-14",
                "date_of_death": null,
                "email": "adichter@knesset.gov.il",
                "end_date": null,
                "family_status": "נשוי",
                "fax": "02-6496404",
                "gender": "זכר",
                "id": 771,
                "img_url": "http://www.knesset.gov.il/mk/images/members/dicter_abraham-s.jpg",
                "is_current": true,
                "name": "אבי (משה) דיכטר",
                "number_of_children": 3,
                "party_name": "קדימה",
                "party_url": "/party/6/%D7%A7%D7%93%D7%99%D7%9E%D7%94/",
                "phone": "02-6408515",
                "place_of_birth": "אשקלון, ישראל",
                "place_of_residence": "אשקלון",
                "place_of_residence_lat": "31.6666667",
                "place_of_residence_lon": "34.5666667",
                "residence_centrality": 6,
                "residence_economy": 5,
                "resource_uri": "/api/v2/member/771/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/797/",
                "average_monthly_committee_presence": 2.08,
                "average_weekly_presence_hours": 9.2,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 0,
                "bills_stats_proposed": 13,
                "bills_uri": "/api/v2/bill/?proposer=797",
                "current_role_descriptions": null,
                "date_of_birth": "1948-01-15",
                "date_of_death": null,
                "email": "abraverman@knesset.gov.il",
                "end_date": null,
                "family_status": "נשוי",
                "fax": "",
                "gender": "זכר",
                "id": 797,
                "img_url": "http://www.knesset.gov.il/mk/images/members/braverman_avishay-s.jpg",
                "is_current": true,
                "name": "אבישי ברוורמן",
                "number_of_children": 2,
                "party_name": "העבודה",
                "party_url": "/party/3/%D7%94%D7%A2%D7%91%D7%95%D7%93%D7%94/",
                "phone": "02-675-3333",
                "place_of_birth": "ישראל",
                "place_of_residence": "תל אביב",
                "place_of_residence_lat": "32.0554",
                "place_of_residence_lon": "34.7595",
                "residence_centrality": 10,
                "residence_economy": 8,
                "resource_uri": "/api/v2/member/797/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/800/",
                "average_monthly_committee_presence": 1.08,
                "average_weekly_presence_hours": 16.2,
                "bills_stats_approved": 0,
                "bills_stats_first": 1,
                "bills_stats_pre": 2,
                "bills_stats_proposed": 21,
                "bills_uri": "/api/v2/bill/?proposer=800",
                "current_role_descriptions": null,
                "date_of_birth": "1959-02-02",
                "date_of_death": null,
                "email": "isarsur@knesset.gov.il",
                "end_date": null,
                "family_status": "נשוי",
                "fax": "02-6408910",
                "gender": "זכר",
                "id": 800,
                "img_url": "http://www.knesset.gov.il/mk/images/members/sarsur_ibrahim-s.jpg",
                "is_current": true,
                "name": "אברהים צרצור",
                "number_of_children": 1,
                "party_name": "רע\"מ-תע\"ל",
                "party_url": "/party/10/%D7%A8%D7%A2%22%D7%9E-%D7%AA%D7%A2%22%D7%9C/",
                "phone": "02-6408415",
                "place_of_birth": "כפר קאסם, ישראל",
                "place_of_residence": "כפר קאסם",
                "place_of_residence_lat": "32.1151",
                "place_of_residence_lon": "34.9751",
                "residence_centrality": 7,
                "residence_economy": 3,
                "resource_uri": "/api/v2/member/800/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            }
        ]
    }

Some things to note:

  * By default, you get a paginated set of objects (1000 per page in the above
    example).
  * In the ``meta``, you get a ``previous`` & ``next``. If available, these are
    URIs to the previous & next pages.
  * You get a list of resources/objects under the ``objects`` key.
  * Each resources/object has a ``resource_uri`` field that points to the
    detail view for that object.
  * The foreign key to ``agend`` is represented as a URI by ``agenda_uri``.

If you want to skip paginating, simply run::

    curl http://oknesset.org/api/v2/member/?limit=0

Be warned this will return all objects, so it may be a CPU/IO-heavy operation
on large datasets.

Let's try filtering on the resource. Since we know we can filter on the
``is_current`` (from ``filters`` in the schema), we'll fetch all members which
aren't current (note ``total_count`` in ``meta``)::

    curl http://oknesset.org/api/v2/member/?is_current=False

We get back what we asked for::

    {

        "meta": {
            "limit": 1000,
            "next": null,
            "offset": 0,
            "previous": null,
            "total_count": 8
        },
        "objects": [
            {
                "agendas_uri": "/api/v2/member-agendas/100/",
                "average_monthly_committee_presence": 15.84,
                "average_weekly_presence_hours": 11,
                "bills_stats_approved": 3,
                "bills_stats_first": 4,
                "bills_stats_pre": 13,
                "bills_stats_proposed": 120,
                "bills_uri": "/api/v2/bill/?proposer=100",
                "current_role_descriptions": null,
                "date_of_birth": "1961-07-11",
                "date_of_death": null,
                "email": "pinespaz@knesset.gov.il",
                "end_date": "2010-01-10",
                "family_status": "נשוי",
                "fax": "02-6496172",
                "gender": "זכר",
                "id": 100,
                "img_url": "http://www.knesset.gov.il/mk/images/members/pinespaz_ofir-s.jpg",
                "is_current": false,
                "name": "אופיר פינס-פז",
                "number_of_children": 2,
                "party_name": "העבודה",
                "party_url": "/party/3/%D7%94%D7%A2%D7%91%D7%95%D7%93%D7%94/",
                "phone": "02-6408809",
                "place_of_birth": "ראשון לציון, ישראל",
                "place_of_residence": "",
                "place_of_residence_lat": null,
                "place_of_residence_lon": null,
                "residence_centrality": 8,
                "residence_economy": 8,
                "resource_uri": "/api/v2/member/100/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/730/",
                "average_monthly_committee_presence": 2.93,
                "average_weekly_presence_hours": 10.1,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 3,
                "bills_stats_proposed": 18,
                "bills_uri": "/api/v2/bill/?proposer=730",
                "current_role_descriptions": null,
                "date_of_birth": "1952-09-08",
                "date_of_death": null,
                "email": "eaflalo@knesset.gov.il",
                "end_date": "2012-01-25",
                "family_status": "",
                "fax": "02-6496164",
                "gender": "זכר",
                "id": 730,
                "img_url": "http://www.knesset.gov.il/mk/images/members/aflalo_eli-s.jpg",
                "is_current": false,
                "name": "אלי אפללו",
                "number_of_children": 3,
                "party_name": "קדימה",
                "party_url": "/party/6/%D7%A7%D7%93%D7%99%D7%9E%D7%94/",
                "phone": "02-6408468",
                "place_of_birth": "קזבלנקה, מרוקו",
                "place_of_residence": "עפולה",
                "place_of_residence_lat": "32.6077778",
                "place_of_residence_lon": "35.2897222",
                "residence_centrality": 5,
                "residence_economy": 5,
                "resource_uri": "/api/v2/member/730/",
                "start_date": "2009-02-24",
                "year_of_aliyah": 1962
            },
            {
                "agendas_uri": "/api/v2/member-agendas/16/",
                "average_monthly_committee_presence": 0.32,
                "average_weekly_presence_hours": 6.1,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 1,
                "bills_stats_proposed": 13,
                "bills_uri": "/api/v2/bill/?proposer=16",
                "current_role_descriptions": null,
                "date_of_birth": "1943-04-30",
                "date_of_death": "2011-03-18",
                "email": "zeevb@knesset.gov.il",
                "end_date": "2011-03-18",
                "family_status": "נשוי",
                "fax": "02-6496062",
                "gender": "זכר",
                "id": 16,
                "img_url": "http://www.knesset.gov.il/mk/images/members/boim_zev-s.jpg",
                "is_current": false,
                "name": "זאב בוים",
                "number_of_children": 3,
                "party_name": "קדימה",
                "party_url": "/party/6/%D7%A7%D7%93%D7%99%D7%9E%D7%94/",
                "phone": "02-6408411",
                "place_of_birth": "ירושלים, ישראל",
                "place_of_residence": "הרצליה",
                "place_of_residence_lat": "32.1682",
                "place_of_residence_lon": "34.8125",
                "residence_centrality": 8,
                "residence_economy": 8,
                "resource_uri": "/api/v2/member/16/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/5/",
                "average_monthly_committee_presence": 20.55,
                "average_weekly_presence_hours": 18.9,
                "bills_stats_approved": 3,
                "bills_stats_first": 3,
                "bills_stats_pre": 14,
                "bills_stats_proposed": 111,
                "bills_uri": "/api/v2/bill/?proposer=5",
                "current_role_descriptions": null,
                "date_of_birth": "1940-03-26",
                "date_of_death": null,
                "email": "horon@knesset.gov.il",
                "end_date": "2011-03-25",
                "family_status": "נשוי",
                "fax": "02-6408904",
                "gender": "זכר",
                "id": 5,
                "img_url": "http://www.knesset.gov.il/mk/images/members/oron_chaim-s.jpg",
                "is_current": false,
                "name": "חיים אורון",
                "number_of_children": 4,
                "party_name": "מרצ",
                "party_url": "/party/11/%D7%9E%D7%A8%D7%A6/",
                "phone": "02-6408348",
                "place_of_birth": "תל אביב, ישראל",
                "place_of_residence": "קיבוץ להב",
                "place_of_residence_lat": "31.379361",
                "place_of_residence_lon": "34.871292",
                "residence_centrality": 5,
                "residence_economy": 7,
                "resource_uri": "/api/v2/member/5/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/115/",
                "average_monthly_committee_presence": 0.94,
                "average_weekly_presence_hours": null,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 0,
                "bills_stats_proposed": 0,
                "bills_uri": "/api/v2/bill/?proposer=115",
                "current_role_descriptions": null,
                "date_of_birth": "1950-04-10",
                "date_of_death": null,
                "email": "",
                "end_date": "2009-07-02",
                "family_status": "",
                "fax": "",
                "gender": "זכר",
                "id": 115,
                "img_url": "http://www.knesset.gov.il/mk/images/members/ramon_haim-s.jpg",
                "is_current": false,
                "name": "חיים רמון",
                "number_of_children": null,
                "party_name": "קדימה",
                "party_url": "/party/6/%D7%A7%D7%93%D7%99%D7%9E%D7%94/",
                "phone": "",
                "place_of_birth": "יפו, ישראל",
                "place_of_residence": "",
                "place_of_residence_lat": null,
                "place_of_residence_lon": null,
                "residence_centrality": null,
                "residence_economy": null,
                "resource_uri": "/api/v2/member/115/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/697/",
                "average_monthly_committee_presence": 1.02,
                "average_weekly_presence_hours": 9.9,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 2,
                "bills_stats_proposed": 12,
                "bills_uri": "/api/v2/bill/?proposer=697",
                "current_role_descriptions": null,
                "date_of_birth": "1954-02-26",
                "date_of_death": null,
                "email": "ytamir@knesset.gov.il",
                "end_date": "2010-04-13",
                "family_status": "גרושה",
                "fax": "02-6753976",
                "gender": "נקבה",
                "id": 697,
                "img_url": "http://www.knesset.gov.il/mk/images/members/tamir_yuli-s.jpg",
                "is_current": false,
                "name": "יולי תמיר",
                "number_of_children": 2,
                "party_name": "העבודה",
                "party_url": "/party/3/%D7%94%D7%A2%D7%91%D7%95%D7%93%D7%94/",
                "phone": "02-6753437",
                "place_of_birth": "ישראל",
                "place_of_residence": "תל אביב?",
                "place_of_residence_lat": null,
                "place_of_residence_lon": null,
                "residence_centrality": 10,
                "residence_economy": 8,
                "resource_uri": "/api/v2/member/697/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/103/",
                "average_monthly_committee_presence": 0.21,
                "average_weekly_presence_hours": 5.2,
                "bills_stats_approved": 0,
                "bills_stats_first": 0,
                "bills_stats_pre": 0,
                "bills_stats_proposed": 1,
                "bills_uri": "/api/v2/bill/?proposer=103",
                "current_role_descriptions": null,
                "date_of_birth": "1955-06-11",
                "date_of_death": null,
                "email": "mporush@knesset.gov.il",
                "end_date": "2011-02-06",
                "family_status": "נשוי",
                "fax": "02-6408914",
                "gender": "זכר",
                "id": 103,
                "img_url": "http://www.knesset.gov.il/mk/images/members/porush_meir-s.jpg",
                "is_current": false,
                "name": "מאיר פרוש",
                "number_of_children": 12,
                "party_name": "יהדות התורה",
                "party_url": "/party/4/%D7%99%D7%94%D7%93%D7%95%D7%AA-%D7%94%D7%AA%D7%95%D7%A8%D7%94/",
                "phone": "02-6408428",
                "place_of_birth": "ירושלים, ישראל",
                "place_of_residence": "ירושלים",
                "place_of_residence_lat": "31.7857",
                "place_of_residence_lon": "35.2007",
                "residence_centrality": 9,
                "residence_economy": 4,
                "resource_uri": "/api/v2/member/103/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            },
            {
                "agendas_uri": "/api/v2/member-agendas/45/",
                "average_monthly_committee_presence": 0.53,
                "average_weekly_presence_hours": 14.2,
                "bills_stats_approved": 3,
                "bills_stats_first": 4,
                "bills_stats_pre": 4,
                "bills_stats_proposed": 13,
                "bills_uri": "/api/v2/bill/?proposer=45",
                "current_role_descriptions": null,
                "date_of_birth": "1957-02-26",
                "date_of_death": null,
                "email": "zhanegbi@knesset.gov.il",
                "end_date": "2010-11-09",
                "family_status": "נשוי",
                "fax": "02-6753100",
                "gender": "זכר",
                "id": 45,
                "img_url": "http://www.knesset.gov.il/mk/images/members/hanegbi_tzahi-s.jpg",
                "is_current": false,
                "name": "צחי הנגבי",
                "number_of_children": 4,
                "party_name": "קדימה",
                "party_url": "/party/6/%D7%A7%D7%93%D7%99%D7%9E%D7%94/",
                "phone": "02-6408532",
                "place_of_birth": "ירושלים, ישראל",
                "place_of_residence": "מבשרת ציון",
                "place_of_residence_lat": "31.7994444",
                "place_of_residence_lon": "35.1488889",
                "residence_centrality": 7,
                "residence_economy": 8,
                "resource_uri": "/api/v2/member/45/",
                "start_date": "2009-02-24",
                "year_of_aliyah": null
            }
        ]

    }

Where there were 128 members before, now there are only eight.


Getting A Detail Resource
-------------------------

Since each resource/object in the list view had a ``resource_uri``, let's
explore what's there::

    curl http://oknesset.org/api/v2/member/123/

We get back a similar set of data that we received from the list view::

    {

        "agendas_uri": "/api/v2/member-agendas/123/",
        "average_monthly_committee_presence": 0.51,
        "average_weekly_presence_hours": 7.6,
        "bills_stats_approved": 0,
        "bills_stats_first": 0,
        "bills_stats_pre": 0,
        "bills_stats_proposed": 0,
        "bills_uri": "/api/v2/bill/?proposer=123",
        "current_role_descriptions": "שר התעשייה, המסחר והתעסוקה",
        "date_of_birth": "1956-12-07",
        "date_of_death": null,
        "email": "ssimhon@knesset.gov.il",
        "end_date": null,
        "family_status": "נשוי",
        "fax": "02-6496187",
        "gender": "זכר",
        "id": 123,
        "img_url": "http://www.knesset.gov.il/mk/images/members/simhon_shalom-s.jpg",
        "is_current": true,
        "name": "שלום שמחון",
        "number_of_children": 2,
        "party_name": "העצמאות",
        "party_url": "/party/13/%D7%94%D7%A2%D7%A6%D7%9E%D7%90%D7%95%D7%AA/",
        "phone": "02-6408385",
        "place_of_birth": "ישראל",
        "place_of_residence": "אבן מנחם",
        "place_of_residence_lat": "33.0738889",
        "place_of_residence_lon": "35.295",
        "residence_centrality": 3,
        "residence_economy": 5,
        "resource_uri": "/api/v2/member/123/",
        "start_date": "2009-02-24",
        "year_of_aliyah": null

    }

Where this proves useful (for example) is present in the data we got back. We
know the URI of the ``agenda`` associated with this member. Let's run::

    curl http://oknesset.org/api/v2/member-agendas/123/

Without ever seeing any aspect of the member's ``agenda`` & just following the URI
given, we get back::

    {

        "agendas": [
            {
                "absolute_url": "/agenda/52/",
                "id": 52,
                "max": 49.08,
                "min": -22.52,
                "name": "המדד החברתי",
                "owner": "המשמר החברתי",
                "party_max": 2.15,
                "party_min": -11.72,
                "rank": 79,
                "score": -4.42
            },
            {
                "absolute_url": "/agenda/9/",
                "id": 9,
                "max": 83.33,
                "min": -33.33,
                "name": "חיזוק הפריפריה",
                "owner": "צוות כנסת פתוחה",
                "party_max": 0,
                "party_min": -33.33,
                "rank": 94,
                "score": -16.67
            },
            {
                "absolute_url": "/agenda/7/",
                "id": 7,
                "max": 80.95,
                "min": -71.43,
                "name": "סיוע לנזקקים",
                "owner": "צוות כנסת פתוחה",
                "party_max": -11.9,
                "party_min": -52.38,
                "rank": 69,
                "score": -21.43
            },
            {
                "absolute_url": "/agenda/1/",
                "id": 1,
                "max": 40.77,
                "min": -21.54,
                "name": "ימין מדיני בטחוני",
                "owner": "מטות ערים",
                "party_max": 11.54,
                "party_min": -0.77,
                "rank": 58,
                "score": 3.85
            },
            {
                "absolute_url": "/agenda/6/",
                "id": 6,
                "max": 32.69,
                "min": -37.82,
                "name": "שירות אזרחי ושוויון בנטל",
                "owner": "צוות כנסת פתוחה",
                "party_max": -2.56,
                "party_min": -12.82,
                "rank": 77,
                "score": -12.18
            },
            {
                "absolute_url": "/agenda/24/",
                "id": 24,
                "max": 69.23,
                "min": -65.38,
                "name": "שיוויון הזדמנויות",
                "owner": "אבטלה סמויה",
                "party_max": -15.38,
                "party_min": -34.62,
                "rank": 108,
                "score": -34.62
            },
            {
                "absolute_url": "/agenda/20/",
                "id": 20,
                "max": 53.33,
                "min": -21.67,
                "name": "קידום מעמד הנשים",
                "owner": "צוות כנסת פתוחה",
                "party_max": 21.67,
                "party_min": 3.33,
                "rank": 80,
                "score": 5
            },
            {
                "absolute_url": "/agenda/45/",
                "id": 45,
                "max": 72.66,
                "min": -38.31,
                "name": "ציונות דתית לאומית",
                "owner": "יעקב פייגלין",
                "party_max": 26.42,
                "party_min": 4.23,
                "rank": 49,
                "score": 26.42
            },
            {
                "absolute_url": "/agenda/43/",
                "id": 43,
                "max": 64.5,
                "min": -35.5,
                "name": "קידום השוויון בין המינים",
                "owner": " הלובי לשיוויון בין המינים",
                "party_max": 23.67,
                "party_min": 3.55,
                "rank": 45,
                "score": 15.38
            },
            {
                "absolute_url": "/agenda/26/",
                "id": 26,
                "max": 79.02,
                "min": -65.03,
                "name": "הפרדת דת ומדינה",
                "owner": "המרכז הרפורמי לדת ומדינה",
                "party_max": 0,
                "party_min": -41.96,
                "rank": 105,
                "score": -41.96
            },
            {
                "absolute_url": "/agenda/36/",
                "id": 36,
                "max": 52.72,
                "min": -23.72,
                "name": "קיימות",
                "owner": "העמותה הישראלית לכלכלה בת קיימא",
                "party_max": 7.08,
                "party_min": -8.9,
                "rank": 78,
                "score": -0.33
            },
            {
                "absolute_url": "/agenda/41/",
                "id": 41,
                "max": 77.7,
                "min": -85.01,
                "name": "זכויות אדם",
                "owner": "אלון",
                "party_max": -0.72,
                "party_min": -27.34,
                "rank": 67,
                "score": -18.71
            },
            {
                "absolute_url": "/agenda/39/",
                "id": 39,
                "max": 47.72,
                "min": -12.21,
                "name": "הקטנת ריכוזיות ועידוד תחרותיות במשק",
                "owner": "אלון",
                "party_max": 12.54,
                "party_min": -6.51,
                "rank": 70,
                "score": 4.89
            },
            {
                "absolute_url": "/agenda/40/",
                "id": 40,
                "max": 51.79,
                "min": -13.85,
                "name": "שיפור הדמוקרטיה הפרלמנטרית",
                "owner": "ישראלים להצלת הדמוקרטיה",
                "party_max": 38.46,
                "party_min": -10.26,
                "rank": 96,
                "score": -3.08
            },
            {
                "absolute_url": "/agenda/48/",
                "id": 48,
                "max": 60.49,
                "min": -24.69,
                "name": "הסדרת נציגות הורים במערכת החינוך",
                "owner": "נבות",
                "party_max": 60.49,
                "party_min": 24.69,
                "rank": 34,
                "score": 24.69
            },
            {
                "absolute_url": "/agenda/53/",
                "id": 53,
                "max": 13.26,
                "min": -30.73,
                "name": "מדד החופש",
                "owner": "התנועה הליברלית החדשה, הפורום הליברלי בליכוד ",
                "party_max": 6.6,
                "party_min": 2.4,
                "rank": 28,
                "score": 2.4
            },
            {
                "absolute_url": "/agenda/47/",
                "id": 47,
                "max": 83.33,
                "min": -16.67,
                "name": "העסקה ישירה של כלל העובדים/ות בישראל",
                "owner": "הקואליציה הארצית להעסקה ישירה",
                "party_max": 16.67,
                "party_min": -16.67,
                "rank": 36,
                "score": 16.67
            },
            {
                "absolute_url": "/agenda/49/",
                "id": 49,
                "max": 87.15,
                "min": -20.08,
                "name": "סביבה ופיתוח בר-קיימא",
                "owner": "חיים וסביבה",
                "party_max": 8.03,
                "party_min": -8.03,
                "rank": 87,
                "score": -3.21
            },
            {
                "absolute_url": "/agenda/55/",
                "id": 55,
                "max": 35.71,
                "min": -81.63,
                "name": "רציונליות סביבתית",
                "owner": "צוות \"הבלוג הירוק\"",
                "party_max": 6.12,
                "party_min": -9.18,
                "rank": 38,
                "score": 0
            }
        ],
        "resource_uri": "/api/v2/member-agendas/123/"

    }

You can do a similar fetch using the following Javascript/jQuery (though be
wary of same-domain policy)::

    $.ajax({
      url: 'http://oknesset.org/api/v2/member-agendas/123/',
      type: 'GET',
      accepts: 'application/json',
      dataType: 'json'
    })



.. note::

    TODO: PUT, POST, DELETE, PATCH and bulk operations are removed as
    they're disabled for now.

    Should re-add and adjust to okneseet.org as they are enabled.


