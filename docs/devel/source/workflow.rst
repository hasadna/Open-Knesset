.. _devel_workflow:

=========================
Development Workflow
=========================

Congratulations, we have everything installed, now it's time to start working on
the project. The following describes various scenarios.

.. important::

    - MS Windows users: replace ``./manage.py`` with ``python manage.py``
    - Run the manage.py commands from the `Open-Knesset` directory, with the
      **virtualenv activated**.


Before Coding
==========================

We need to make sure we're in sync with changes done by others (upstream).

.. important::

    Please do this every time before you start developing:

Update the code and requirements
--------------------------------------

Enter the `Open-Knesset` directory, and run:

.. code-block:: sh

    git pull git@github.com:hasadna/Open-Knesset.git master

If `requirements.txt` was modified, make sure all of them are installed (no harm
running this command event in case of no changes):

    `pip install -r requirements.txt`

.. note::

    We recommend running the pip command from the parent diretory (the
    virtualenv's root), as it may create an ``src`` directory when pulling
    packages from git repos. in that case::


        `pip install -r Open-Knesset/requirements.txt`



Run migrations and tests
--------------------------------

.. code-block:: sh

    ./manage.py migrate
    ./manage.py test

if there are any failures, contact the other developers in the `oknesset-dev`_
group to see if that's something you should worry about.

.. _oknesset-dev: https://groups.google.com/forum/#!forum/oknesset-dev


See :ref:`devel_tips` for a few bash functions that may help.

While Coding
==============

General
---------

- Write tests for everything that you code.
- Keep performance in mind - test the number of db queries your code performs
  using ``./manage.py runserver`` and accessing a page that runs the code you
  changed. See the output of the dev-server before and after your change.


Adding a field to existing model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use South_ to manage database schema migrations. The work process is:

- Add the field you want to model `SampleModel` in app `sample_app`
- `python manage.py schemamigration sample_app --auto` this generates a new migration
  under sample_app/migrations. You should review it to make sure it does what
  you've expected.
- `python manage.py migrate` runs the migration against the database.
- Don't forget to **git add** and **commit** the migration file.

.. _South: http://south.aeracode.org/

After you code
~~~~~~~~~~~~~~~~

- ``./manage.py test`` # make sure you didn't break anything
- ``git status`` # to see what changes you made
- ``git diff filename`` # to see what changed in a specific file
- ``git add filename`` # for each file you changed/added.
- ``git commit -m "commit message"`` 
  
  Please write a sensible commit message, and include "fix#: [number]" of the issue number you're working on (if any).
- ``git push`` # push changes to git repo
- go to github.com and send a "pull request" so your code will be reviewed and
  pulled into the main branch, make sure the base repo is
  **hasadna/Open-Knesset**.
