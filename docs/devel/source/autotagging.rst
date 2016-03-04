.. autotagging:

=======
Intro
=======

Auto tagging is used to create auto tags out of the explanition info of a private proposal.
It uses machine learning techniques.

======
Flow
======

* Reading - Read the data from the server using API.
* Parsing - Parse the downloaded HTML files of the PP.
* Building - Make histograms out of the parsed HTML.
* Train/Test the information.

Reading
=========

Run:

.. code-block:: sh

    python read_pp.py

Parsing
=========

Run:

.. code-block:: sh

    python parse_htmls.py

Building
==========

Run:

.. code-block:: sh

    python make_histograms.py

Training/Testing
==================

Auto tagging is in testing phase, so no auto-tagging script exist.
To execute the test, run:

.. code-block:: sh

    python tags_autolearn_play.py

Building HTML
===============

This is used to understand to find errors in the tagging process. Just use your logic here. 
To execute the test, run:

.. code-block:: sh

    python build_important_keyword_html.py

