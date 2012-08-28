Architecure
===========

Open Knesset architecture is based on three requirments:

- the need to smartly harvest and store data from ancient offical sites
- simple and friendly frontend development
- complete API to support friendly developers

Version 1.0 was made from a single Django based server that scraped the
official site, rendered templates and serverd a read-only API.
It worked quite well for over 1K days, but with time, the templates became
a ball of design and logic spaghetti, making it too complex for designers.
More than that, Django templates and custom templatetags made it easy for
us to hit the db and kill performance through simple loops.

For 2.0, we want to keep the templates easy enough for designers to grok,
and renedring to be fast. We decided to prevent developers from adding template
logic and start using a logic-less template system - `Mustache`_.
That decision led to `ok-webfront`_ -
a simple server that proxies the API server and renders the templates. 

As simplicity is key, we've decided to keep the number of languages used in the 
frontend server to just one - javascript - and use `nodejs`_ and `expressjs`_ as 
the server and app frameworks.
It seems to be working as opposed to the hours is takes designers to install
Open Knesset, ok-webfront is installed in a ¼ hour. 

  NOTE: We're using Bootstrap as the design framework, so designer can use their
  knowledge.

For the original project version 2.0 means a a new version of
the API and losing its html rendering ability. From now on, Open Knesset is
focused on scraping the official sites, storing user content and serving
it all through an API [#todo1]_. The new API is served using `django-tastypie`_ a powerful
pluggable app that makes it easy to code powerful handlers. With tastypie every 
app gets an `api.py` to define the classes of the app's resources.

.. _Mustache: http://mustache.github.com/
.. _ok-webfront: https://github.com/daonb/ok-webfront
.. _nodejs: http://nodejs.org
.. _expressjs: http://expressjs.com
.. _django-tastypie: https://github.com/toastdriven/django-tastypie
.. [#todo1]  TODO: Develop ok_backuser, a document store for all user content to
             enable ok_webfront developers to easily add new users' data
