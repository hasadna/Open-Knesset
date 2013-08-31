===========
Linux
===========

Installing Initial Requirements
=================================

On Linux we'll be creating a clean virtualenv, so in addtion we'll need
developer tools (to compile PIL, lxml etc).

Debian and derivatives like Ubuntu and Mint
--------------------------------------------

.. code-block:: sh

    sudo apt-get install build-essential git python python-dev python-setuptools python-virtualenv python-pip
    sudo apt-get build-dep python-imaging
    sudo apt-get build-dep python-lxml


Fedora
-----------

.. code-block:: sh

    sudo yum groupinstall "Development Tools" "Development Libraries"
    sudo yum install git python python-devel python-setuptools python-virtualenv python-pip libjpeg-turbo-devel libpng-devel libxml2-devel libxslt-devel


Creating and Activating the virtualenv
===========================================

Navigate in a terminal to the directory you want the
environment created in (usually under your home directory). We'll name the
created environment ``oknesset``. 

Once in that directory:

.. code-block:: sh

    virtualenv oknesset

.. warning::

    In case you have both Python 2 and 3 installed, please make sure the virtualenv
    is created with Python 2. If that's not the case, pass the correct python
    executable to the virtualenv command. e.g:

    .. code-block:: sh

        virtualenv -p python2 oknesset

    To check which is the default interpreter virtualenv will use, run
    ``virtualenv -h`` and check in the output the default for `-p` flag.
    
We need to `activate` the virtual environment (it mainly modifies the paths so
that correct packages and bin directories will be found) each time we wish to
work on the code.

In Linux we'll source the activation script (to set env vars):

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

.. _github guide on ssh keys: https://help.github.com/articles/generating-ssh-keys#platform-linux


Installing requirements
=============================

Still in the terminal with the virtualenv activated, inside the *oknesset* directory,
run:

.. code-block:: sh

    pip-2.7 install -r Open-Knesset/requirements.txt
    
And wait ...

Once done, proceed to :ref:`tests_develdb`.
