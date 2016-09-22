============
Bills / Laws
============

Bills / Laws are scraped using the syncdata process.

There are 3 relevant functions in the syncdata process which are run in this order:

update_laws_data
================

Downloads private laws from the last 4 pages:

* http://www.knesset.gov.il/privatelaw/plaw_display.asp?LawTp=2&RowStart=0
* http://www.knesset.gov.il/privatelaw/plaw_display.asp?LawTp=2&RowStart=26
* http://www.knesset.gov.il/privatelaw/plaw_display.asp?LawTp=2&RowStart=52
* http://www.knesset.gov.il/privatelaw/plaw_display.asp?LawTp=2&RowStart=78

Extracts the law name and law pdf link, then iterates through last 200 votes and try to match vote title to law title.

If a match is found - save the law summary in vote summary and link the pdf to the vote.

If vote doesn't have full_text - it is taken from the laws .rtf file


parse_laws
==========

Iterate over these pages: http://www.knesset.gov.il/privatelaw/Plaw_display.asp?lawtp=1 from knesset start date

parses the data from the html


find_proposals_in_other_data
============================

* TODO

merge_duplicate_laws
====================

* TODO

update_gov_law_decisions
========================

* TODO
