Flow Samples
============

Viewing a member
----------------

When a client hits the url http://web.oknesset.org/member/200/ the
server gets a request.
It then tries to get the content from
http://api.oknesset.org/api/v2/member/200/.
When the context arrives, ok-webfront uses it to render the template from
`/views/member/show.html` and replies to the client. Later, client-based
code can request further API data, accessing the API server directly.
