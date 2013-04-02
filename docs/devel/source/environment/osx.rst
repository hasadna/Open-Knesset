=======
OS X
=======

.. important::

    The info here is based on the post
    `Fixing Python, virtualenv and pip on Mountain Lion`_

.. _Fixing Python, virtualenv and pip on Mountain Lion: http://blog.dyve.net/fixing-python-virtualenv-and-pip-on-mountain

Command Line Tools
=====================

* Go to https://developer.apple.com/downloads
* Search for "command line tools"
* Download and install the version right for your OS

Install pip and virtualenv
========================================

.. code-block:: sh

    sudo easy_install pip
    sudo pip install virtualenv

Install basic dependencies
========================================

Install homebrew:

.. code-block:: sh

    ruby -e "$(curl -fsSkL raw.github.com/mxcl/homebrew/go)"

Install binary python libraries build dependencies:

.. code-block:: sh

    brew install jpeg libpng libxml2 libxslt
    
Add locale settings (in case you're not UTF-8), put in your ``~/.profile``:


.. code-block:: bash

    export LANG="en_US.UTF-8"
    export LC_COLLATE="en_US.UTF-8"
    export LC_CTYPE="en_US.UTF-8"
    export LC_MESSAGES="en_US.UTF-8"
    export LC_MONETARY="en_US.UTF-8"
    export LC_NUMERIC="en_US.UTF-8"
    export LC_TIME="en_US.UTF-8"
    export LC_ALL=

And source them (to have them updated in the current shell):

.. code-block:: sh

    source ~/.profile


Creating and Activating the virtualenv
===========================================

Navigate in a terminal to the directory you want the
environment created in (usually under your home directory). We'll name the
created environment ``oknesset``. 

Once in that directory:

.. code-block:: sh

    virtualenv oknesset

We need to `activate` the virtual environment (it mainly modifies the paths so
that correct packages and bin directories will be found) each time we wish to
work on the code.

To do it, we'll source the activation script (to set env vars):

.. code-block:: sh

    cd oknesset/
    . bin/activate

Note the changed prompt which includes the virtualenv's name.


Getting the Source Code (a.k.a Cloning)
=========================================

Now we'll clone the forked repository into the virutalenv.  Make sure you're in
the `oknesset` directory and run::

    git clone https://github.com/your-username/Open-Knesset.git

Replace `your-username` with the username you've registered at git hub.

.. note::

    You can also clone with ssh keys, in that case follow the
    `github guide on ssh keys`_. Once you've done that, your clone command
    will look like::

        git@github.com:your-username/Open-Knesset.git

.. _github guide on ssh keys: https://help.github.com/articles/generating-ssh-keys#platform-mac


Installing requirements
=============================

Still in the terminal with the virtualenv activated, inside the *oknesset* directory,
run:

.. code-block:: sh

    pip install -r Open-Knesset/requirements.txt

And wait ...

Once done, proceed to :ref:`tests_develdb`.
