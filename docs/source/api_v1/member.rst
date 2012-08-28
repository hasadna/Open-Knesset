.. index:: API Calls (Member), Examples (Member)

Member API
======================

Each member entry in the response will contain the following fields (some may be
optional or `null`):

**name** {string}
    Member name in Hebrew
**roles** {string}
    Comma separated list of member roles
**party** {String}
    Party this member belongs to
**url** {String}
    the relative url for the Open Knesset's web page of this member
    (# BUG: should be a full url)
**img_url** {String}
    the small image url from the official Knesset site

    .. tip::

        remove the trailing "-s" from the filename to get the full-sized image)
**bills_proposed** {number}
    the number of bills proposed (but not yet have passed on to the voting
    phase) by this member
**bills_passed_pre_vote** {number}
    the number of bills that has passed to the voting phase (but not yet voted on) by this member
**bills_passed_first_vote** {number}
    the number of bills that passed the first vote (out of three) by this member
**bills_approved** {number}
    number of bills that passed all three votes, and are approved, by this member.
**committees** {Array of arrays}
     Each array represents one committee this member belongs to; this array
     contains exactly 2 elements:

     * {String} representing the committee name in Hebrew.
     *  {String} that is the relative URL for the committee page in the Open Knesset
**service_time** {number}
    number of days this member has served in the Knesset (consecutive days? Total days?)
**average_weekly_presence_rank** {number}
    TBD
**votes_count** {number}
    number of votes this member has participated in
**id** {number}
    the unique member id
**committee_meetings_per_month** {number}
    Average number of attended committee meetings per month
**average_weekly_presence** {number}
    Average number of hours per week attending the knesset
**votes_per_month** {number}
    Average number of votes at the plenum per month
**discipline** {number}
    Percent of voting with the party
**email** {String}
    Member's email address
**phone** {String}
    Member's phone number
**fax** {String}
    Member's fax number
**gender** {String}
    `זכר` or `נקבה`
**place_of_birth** {String}
    Birth place
**year_of_aliyah** {Number}
    Year of migrating (if applicable)
**is_active** {Boolean}
    Is current member of the knesset
**start_date** {Date}
    Starting date at the knesset (YYYY-MM-DD)
**end_date** {Date}
    End date at the knesset, if applicable (YYYY-MM-DD)
**links** {Array of arrays}
    Relevant links for the member (e.g: Facebook page, knesset page etc.). Each
    item in the array is an array with 2 members:

    * {String} Description
    * {String} Url
**residence_economy** {Number}
    Social-Economic status of city of residence
**place_of_residence** {String}
    Place of residence in Hebrew
**place_of_residence_lon** {Number}
    Longitude of residence
**place_of_residence_lat** {Number}
    Latitide of residence
**residence_centrality** {Number}
    Measure of centrality of city of residence (0-10, while 10 is closest to the
    center)
**number_of_children** {Number}
    Number of children according to Knesset's site

.. index::
    Examples (Member); Member info
    API Calls (Member); Member info

Member info
----------------------

Get the info for a specific member id.

:returns: Object of the member info

Example call

.. code-block:: sh

    curl http://oknesset.org/api/member/810/

Response:

.. code-block:: js

    {
        "residence_economy": 7,
        "links": [
            [
                "שלמה (נגוסה) מולה בפייסבוק",
                "http://www.facebook.com/shlomo.molla\n"
            ],
            [
                "שלמה (נגוסה) מולה באתר הכנסת",
                "http://www.knesset.gov.il/mk/heb/mk.asp?mk_individual_id_t=810"
            ]
        ],
        "average_weekly_presence_rank": 4,
        "place_of_residence_lon": "34.8045361",
        "place_of_residence": "ראשון לציון",
        "votes_per_month": 59.100000000000001,
        "id": 810,
        "discipline": 99.0,
        "place_of_residence_lat": "31.9621389",
        "service_time": 1021,
        "family_status": "נשוי",
        "date_of_birth": "1965-11-21",
        "party": "קדימה",
        "img_url": "http://www.knesset.gov.il/mk/images/members/molla_shlomo-s.jpg",
        "email": "smolla@knesset.gov.il",
        "bills_approved": 4,
        "bills_proposed": 145,
        "fax": "02-649-6620",
        "current_role_descriptions": null,
        "end_date": null,
        "average_weekly_presence": 18.800000000000001,
        "area_of_residence": null,
        "date_of_death": null,
        "phone": "02-640-8205",
        "is_current": true,
        "committees": [
            [
                "ועדת הכספים",
                "/committee/9/"
            ],
            [
                "ועדת הכנסת",
                "/committee/1/"
            ],
            [
                "ועדת העלייה, הקליטה והתפוצות",
                "/committee/3/"
            ],
            [
                "ועדת החוקה, חוק ומשפט",
                "/committee/5/"
            ],
            [
                "ועדת הכלכלה",
                "/committee/2/"
            ]
        ],
        "name": "שלמה (נגוסה) מולה",
        "roles": "חבר כנסת באופוזיציה",
        "committee_meetings_per_month": 13.93,
        "url": "/member/810/%D7%A9%D7%9C%D7%9E%D7%94-%D7%A0%D7%92%D7%95%D7%A1%D7%94-%D7%9E%D7%95%D7%9C%D7%94/",
        "gender": "זכר",
        "bills_passed_first_vote": 5,
        "bills_passed_pre_vote": 8,
        "residence_centrality": 9,
        "start_date": "2009-02-24",
        "place_of_birth": "אתיופיה",
        "year_of_aliyah": 1984,
        "votes_count": 2011,
        "number_of_children": 3
    }


.. index::
    Examples (Member); Query members
    API Calls (Member);  Query members

Query Members
-------------------

Search member who's name are a close match to the queried item. Pass the search
terms via GET param `q`.

:return: Array of matching members

Example call

.. code-block:: sh

    curl http://oknesset.org/api/member/?q=דיכטר

Response:

.. code-block:: js

    {
         "name": "אבי (משה) דיכטר",
         "roles": "חבר כנסת באופוזיציה",
         ...
    }


