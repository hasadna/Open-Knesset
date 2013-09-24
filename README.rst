.. important::

    This document contains quick start instruction.
    For more details, **please see** the `Open Knesset developers documentation`_ 

.. _Open Knesset developers documentation: https://oknesset-devel.readthedocs.org/

.. contents::

Installation
==============

GitHub
---------

- Make sure you have an account on GitHub_, and you're logged in.
- Fork the repository_ (top right of page). This creates a copy of the
  repository under your user.
- See http://linux.yyz.us/git-howto.html for a short list of options with
  git and github.com help for more.

.. _GitHib: https://github.com
.. _repository: https://github.com/hasadna/Open-Knesset


Linux
-----------

- Install initial requirements (since we're gonna comile PIL into the environemnt,
  we'll also need development tools):
  
  **Debian and derivatives like Ubuntu and Mint**
  
  .. code-block:: sh
  
      sudo apt-get install build-essential git python python-dev python-setuptools python-virtualenv python-pip
      sudo apt-get build-dep python-imaging
      sudo apt-get build-dep python-lxml
  
  
  **Fedora**
  
  .. code-block:: sh
  
      sudo yum groupinstall "Development Tools" "Development Libraries"
      sudo yum install git python python-devel python-setuptools python-virtualenv python-pip libjpeg-turbo-devel libpng-devel libxml2-devel libxslt-devel


- If you haven't done so already:

  - ``git config --local user.name "Your Name"``
  - ``git config --local user.email "your@email.com"``

- Create the virtual environment. In the terminal cd to the directory you want
  the environment create it and run ``virtualenv oknesset``.

- Activate the virutalenv ``cd oknesset; . bin/activate`` Note the changed
  prompt which includes the virtualenv's name.

- Clone the repository::

    git clone https://github.com/your-username/Open-Knesset.git

  This creates a copy of the project on your local machine.

- Install required packages: ``pip install -r Open-Knesset/requirements.txt``
  and wait ...
- Run the tests::

    cd Open-Knesset
    python manage.py test
    

MS Windows
-----------

- `Download the latest Python 2.7`_ MSI installer matching your architecture
  (32 or 64 bit). As of this writing, the latest one is `2.7.3`_. Install it.
- `Download distribute`_ for your architecture and install it.
- Open command windows and::

    cd c:\Python27\Scripts
    easy_install pip
    pip install virtualenv

- Download and install the installers matching your architecture for PIL_
  and lxml_ (version 2.3.x).
- Download and install `GitHub for Windows`_.
- Run the GitHub program (should have an icon on the desktop). Sign in
  with your username and password.
- Run `Git Shell` (should have an icon on desktop). In that shell create the
  virtualenv::

    cd C:\
    C:\Python27\Scripts\virtualenv --distribute --system-site-packages oknesset
- Still in that shell activate the virutalenv::

    cd oknesset
    Scripts\activate

  Note the changed prompt with includes the virtualenv's name.
- If you haven't already forked the repository (top right of page), do so. 
- Clone the repository. In the `oknesset` directory and run
  ``git clone git@github.com:your-name/Open-Knesset.git``
- Install requirements: ``pip install -r Open-Knesset\requirements.txt`` and
  wait.
- Run the tests::

    cd Open-Knesset
    python manage.py test

.. _Download distribute: http://www.lfd.uci.edu/~gohlke/pythonlibs/#distribute- 
.. _2.7.3: http://www.python.org/download/releases/2.7.3/
.. _Download the latest Python 2.7: http://python.org/download/releases/
.. _PIL: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pil
.. _lxml: http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml
.. _GitHub for Windows: http://windows.github.com


OS X
--------

- Install command line tools. Goto https://developer.apple.com/downloads, 
  Search for "command line tools", download and install the version right for
  your OS
- Install pip and virtualenv::

    sudo easy_install pip
    sudo pip install virtualenv
- Install homebrew: ``ruby -e "$(curl -fsSkL raw.github.com/mxcl/homebrew/go)"``
- Install binary python libraries build dependencies::

  brew install jpeg libpng libxml2 libxslt

- We need UTF-8, Add locale settings (in case you're not UTF-8),
  put in your ``~/.profile``::

    export LANG="en_US.UTF-8"
    export LC_COLLATE="en_US.UTF-8"
    export LC_CTYPE="en_US.UTF-8"
    export LC_MESSAGES="en_US.UTF-8"
    export LC_MONETARY="en_US.UTF-8"
    export LC_NUMERIC="en_US.UTF-8"
    export LC_TIME="en_US.UTF-8"
    export LC_ALL=

  Once done, source them (to have them updated in the current shell)::

    source ~/.profile

- Create the virtual environment. In the terminal cd to the directory you want
  the environment create it and run::

    virtualenv oknesset

- Activate the virutalenv::

    cd oknesset; . bin/activate

  Note the changed prompt which includes the virtualenv's name.

- Clone the repository::

    git clone https://github.com/your-username/Open-Knesset.git

  This creates a copy of the project on your local machine.

- Install required packages::

    pip install -r Open-Knesset/requirements.txt

  and wait ...
- Run the tests::

    cd Open-Knesset
    python manage.py test



After basic installation: Tests and initial db
=================================================

.. note:: Linux users: you can replace ``python manage.py`` with ``./manage.py``.

- Run the tests: ``python manage.py test``
- Download and extract dev.db.zip_ or dev.db.bz2_ (bz2 is smaller), place dev.db
  into the ``Open-Knesset`` directory
- Make sure db schema is upated: ``python manage.py migrate``
- Create a superuser if needed: ``python manage.py createsuperuser``
- To run the development server: ``python manage.py runserver``. Once done, you can
  access it via http://localhost:8000

.. _dev.db.zip: http://oknesset-devdb.s3.amazonaws.com/dev.db.zip
.. _dev.db.bz2: http://oknesset-devdb.s3.amazonaws.com/dev.db.bz2


Working process
===================

Let's describe some development workflow.

Before you code
----------------

.. important::

    - Linux users: you can replace ``python manage.py`` with ``./manage.py``
    - Run the manage.py commands from the `Open-Knesset` directory, with the
      **virtualenv activated**.

Get your branch updated with the changes done by others.
Please do this every time before you start developing.

- ``cd Open-Knesset``
- ``git pull git@github.com:hasadna/Open-Knesset.git master``   Running this command requires having SSH keys registered with github. You can replace 'git@' with 'https://' instead.
- ``pip install -r requirements.txt``  # only needed if the file requirements.txt was changed; but can't hurt you if you run it every time.
- ``python manage.py migrate``              # do not create a superuser account
- ``python manage.py test``                 # if there are any failures, contact the other developers to see if that's something you should worry about.
- ``python manage.py runserver``            # now you can play with the site using your browser

When you code
---------------

General
~~~~~~~~~~~~

- Write tests for everything that you write.
- Keep performance in mind - test the number of db queries your code performs
  using ``python manage.py runserver`` and access a page that runs the code you
  changed. See the output of the dev-server before and after your change.

Adding a field to existing model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use south to manage database migration. The work process looks something like:

- add the field you want to model sample_model in app sample_app
- ``python manage.py schemamigration sample_app --auto`` this generates a new
  migration under `src/knesset/sample_app/migrations`. You should review it to
  make sure it does what you expect.
- ``python manage.py --migrate`` To run un the migration (make the changes on
  the db).
- don't forget to git add/commit the migration file.

Updating the translation strings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently, there is no need to update translation (po) files. Its a real
headache to merge when there are conflicts, so simply add a note to the commit
message "need translations" if you added any _('...') or {% trans '...' %} to
the code.

After you code
~~~~~~~~~~~~~~~~

- ``python manage.py test`` # make sure you didn't break anything
- ``git status`` # to see what changes you made
- ``git diff filename`` # to see what changed in a specific file
- ``git add filename`` # for each file you changed/added.
- ``git commit -m "commit message"``
  
  Please write a sensible commit message, and include "fix#: [number]" of the issue number you're working on (if any).
- ``git push`` # push changes to git repo
- Go to github.com and send a "pull request" so your code will be reviewed and
  pulled into the main branch, make sure the base repo is
  **hasadna/Open-Knesset**.


Known issues
-------------

- Some of the mirrors may be flaky so you might need to install requirements.txt
  several times until all downloads succeed.
- Currently using MySQL as the database engine is not supported

