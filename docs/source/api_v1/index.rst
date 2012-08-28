API Version 1 - Deprecated
==============================

.. warning::
    Version 1 of the API is unmaintained and kept for existing
    application. Please use :ref:`api_v2`

All examples are shown with `curl` from the command line. One can access the URL
and parse the results with their favorite language or tool.

If no format is specified the response will be JSON. For other formats (xml for
now) add the format to the GET params.

e.g:

.. code-block:: sh

    curl http://oknesset.org/api/member/782/?format=xml

.. toctree::
    :maxdepth: 2

    member
    committee
