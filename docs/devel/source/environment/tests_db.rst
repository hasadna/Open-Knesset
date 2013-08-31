.. _tests_develdb:

=============================================
Initial Testing, Development DB & Server
=============================================

After you've installed the base environment, it's time to run the tests and get
an initial development db.

.. important::

    - Linux users: you can replace ``python manage.py`` with ``./manage.py`` for
      less typing
    - Run the manage.py commands from the `Open-Knesset` directory, with the
      virtualenv activated.


Running Tests
==============

.. code-block:: sh

    cd Open-Knesset
    python manage.py test

Download the Development DB
===============================

Download and extract dev.db.zip_ or dev.db.bz2_ (bz2 is smaller). After
unpacking, **place dev.db in the `Open-Knesset` directory**.

.. _dev.db.zip: http://oknesset-devdb.s3.amazonaws.com/dev.db.zip
.. _dev.db.bz2: http://oknesset-devdb.s3.amazonaws.com/dev.db.bz2

To make sure everything is up to date, run the database schema migrations:

.. code-block:: sh

    python manage.py migrate


You might want to create your own superuser:


.. code-block:: sh

    python manage.py createsuperuser


.. _debug_toolbar:

Enable django-debug-toolbar
==============================

.. todo:: Expand on this

Create `local_settings.py` in the `knesset` directory (where `settings.py` is
located). To enable the `django-debug-toolbar`_ on the local developement address,
put in that file:

.. _django-debug-toolbar: http://pypi.python.org/pypi/django-debug-toolbar

.. code-block:: python

    INTERNAL_IPS = ('127.0.0.1',)

Running the Development server
=====================================

To run the development server:

.. code-block:: sh

    python manage.py runserver

Once done, you can access it with your browser via http://localhost:8000 .


Using the debug toolbar
=================================

If you've :ref:`enabled the debug toolbar <debug_toolbar>`, you should see it's
icon on the top right corner of the page:

.. image:: ../_static/djdt.png


Clicking on it will reveal a sidebar which will expose lots of info about the
generated page (templates used, context variables, SQL queries etc.).

We're cool ? Time for some :ref:`devel_workflow`.
