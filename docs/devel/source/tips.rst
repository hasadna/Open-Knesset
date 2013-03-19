.. _devel_tips:

=========================
Development Tips
=========================

IDE setup
=========

Basically you should lookup for virtualenv configuration of your preferred
development environment.


Eclipse with PyDev
~~~~~~~~~~~~~~~~~~

Start by creating a new **PyDev** Project.

.. warning::

    Don't create a Django project! It'll overwrite manage.py and create other
    files. We'll convert it to a Django project later.

.. image:: new_pydev_project.png


* Click "Next" and type a name for the project --- e,g ``OpenKnesset``.
* Uncheck "Use default" if checked, click "Browse", navigate to the virtualenv
  and selected the previously cloned "Open-Knesset" directory.
* Click the link named "Click here to configure an interpreter not listed".

  In the opened window, click "New", and in the opened window "browse". Navigate
  to your virtualenv and select the `python` executable in your `Scripts` folder
  (for MS Windows) or `bin` (on Linux).

  .. image:: pydev_interpreter.png

  Click "OK". A window will popup with folders to be added to python path, click
  "OK". If you get a warning click "Proceed anyways". Let it process the
  libraries and click "OK".

  Now you're back in the Project's dialog.
  Select the interpreter you've just added.
* Make sure "Add project directory to the  PYTHONPATH" is selected.

You should have something like:

.. image:: pydev_project_dialog.png

* Click "Finish", and switch to the PyDev perspective (if the dialog appears).
* Now you should have the project in the PyDev Package explorer (left side).
  In the project. Right click it and select "PyDev" | "Set as Django project".
* Right click the project and select "Properties".
* Select "PyDev - Django", and enter ``manage.py`` int "Django manage.py" and
  ``knesset.settings`` in "Django settings module".

  .. image:: pydev_django_settings.png

  Click "OK".
* Create a run configuration for your project (to make sure it'll find the
  database, etc.):

  * Right click the project, select "Run As" | "Run configurations".
  * Right click "PyDev Django" and select "New".
  * Give it a name (e.g. "oknesset Django")
  * In the Project field click "Browser" and select you project.
  * In Main Module, click browse and select "manage.py".
  * In the "Arguments" tab click, in "Program arguments" enter
    ``runserver --noreload``.
  * Click "Run", you should be able to open your browser and access
    http://localhost:8000 . You can use this run configration from now on.



Useful bash functions
===================================

You can use some variation on these functions when beginning a development session (only after you finished the initial setup).
To use these, paste these functions into your ``~/.bashrc`` file and change the ``~/oknesset/`` in oknesset_activate to the directory where you installed the project's virtualencv. These functions will now be available to you in all future bash sessions, but to get it working in already opened tabs, you'll need to type ``source ~/.bashrc``.

A possible session might include:

* Open a bash tab and run ``oknesset_update`` to pull the new code and db, install any new dependencies and run the tests to check that everything is ok.
* Run ``oknesset_runserver`` in the same tab to launch the development site.
* Open another tab and run ``oknesset_activate`` to enter the Open Knesset directory (and virtualenv) to do any manual work on the files.
* Assuming you have the documentation tools set up and have changed some .rst files, run ``oknesset_makedocs`` to recreate the html pages.

.. code-block:: bash

    oknesset_activate () { #Just enter the Open-Knesset directory and activate the virtualenv
        cd ~/oknesset/ #or wherever you put it

        source bin/activate
        cd Open-Knesset
    }

    oknesset_update () { #Pull the new code and prepare the environment
        oknesset_activate

        wget http://oknesset-devdb.s3.amazonaws.com/dev.db.bz2
        mv dev.db dev.db.old
        bzip2 -d dev.db.bz2
        git pull git@github.com:hasadna/Open-Knesset.git master

        cd ..
        pip install -r requirements.txt
        cd Open-Knesset

        ./manage.py migrate
        ./manage.py test
    }

    oknesset_runserver () { #start the local server
        oknesset_activate
        ./manage.py runserver
    }

    oknesset_makedocs () { #make the documentation html
        oknesset_activate
        pushd docs/devel >/dev/null
        make html
        popd >/dev/null
    }
