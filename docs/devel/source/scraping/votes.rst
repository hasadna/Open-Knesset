=====
Votes
=====

Votes are scraped using the syncdata process, specifically the "update_votes" function.

This functions interates based on vote id corresponding to knesset's vote page, e.g. http://www.knesset.gov.il/vote/heb/Vote_Res_Map.asp?vote_id_t=23556

For the above URL, the vote id is 23556.

We then scrape all the relevant data from that html page, and connect to related objects.

See also the Bills documentation - it updates some data in votes.