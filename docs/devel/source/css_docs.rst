==================================
Working on CSS and Documentation
==================================

CSS
=========

We're using LESS_ (no direct editing of CSS). If you'd like to contribute to the
design efforts:

Before first run, and only once, you'll need::

    git submodule init
    git submodule update


You'll need to have `Node.js`_ installed. After that make sure you have less
installed::

    sudo npm install -g less

Make your changes to the files in the ``less`` directory, and compile the using
(assuming you're in the ``Open-Knesset`` directory)::

    lessc less/app.less static/css/app.css

.. _Node.js: http://nodejs.org/
.. _LESS: http://lesscss.org/#-server-side-usage


Documentation
=================

Our documentation is written with Sphinx_, install it with the virtualenv
activated::

    pip install sphinx


.. _Sphinx: http://sphinx-doc.org/

Edit the relevant docs under the ``docs`` directory, and once done, run
``make html``. You'll have the resulting documentation in ``build/html``
directory.

We have 2 documentation directories:

* api --- API and Embedding for 3rd party apps/services developers
* devel --- Developer guide for the OpenKnesset project (TBD)

e.g: To work on the devel docs, edit the files under ``docs/devel/source``, once
ready to build::

    cd docs/devel
    make html

You'll have the result under::

    docs/devel/build/html

