# About

This is the latest version of total-impact-core. Installing this provides the 
backend and API for the total-impact service. You can then build or run a 
frontend or consume direct from the API into your own frontend.

(Our own frontend is available at [http://github.com/total-impact/total-impact-webapp](http://github.com/total-impact/total-impact-webapp).)

This isn't the deployed version -- it is an in-progress port the old codebase 
at http://github.com/mhahnel/Total-Impact

The deployed version is available at [http://total-impact.org](http://total-impact.org), 
and see [http://total-impact.org/about](http://total-impact.org/about) for more info.


# Dependencies

You may need sudo / root privileges, use if necessary

    apt-get install gcc     
    apt-get install python-lxml
    apt-get install memcached
    apt-get install couchdb
    apt-get install python-setuptools


# Install

This assumes you are running on a recent debian / Ubuntu based server.

Get total-impact-core code by cloning from this repo and cd into the directory.
There are various ways to get code from the repo, here is one example.

    apt-get install git
    git clone https://github.com/total-impact/total-impact-core
    cd total-impact-core

You should consider using a virtualenv too, but it is optional.

How to install:

    python setup.py install

Or to install for dev:

    easy_install pip
    pip install -e .

Check CouchDB is available

    # check couch is up
    curl -X GET http://localhost:5984   # or use your web browser

CouchDB will need patched as there is a bug in couchdb regarding concurrency. Please
see the details at http://code.google.com/p/couchdb-python/issues/detail?id=204
for the patch code and current bug status. It is possible this issue is already 
resolved on your system.

# Config

Total-impact will try to contact CouchDB at http://localhost:5984/ 
When total-impact starts, it will, if necessary, create the database and all necessary views. 

The system can be confirmed by editing totalimpact/default_settings.py 
Alternatively you can create a local config file such as config/local_settings.py and
tell the system to use this config by setting the environment before starting

    export TOTALIMPACT_CONFIG=config/local_settings.py

Any settings you define in local_settings.py would them override the settings in 
default_settings.py. Otherwise, the default value from default_settings.py will be used

# Running

These will only work if install is successful and the CouchDB is available with proper user auth set up.

First start the backend process. This 

    ./runbackend.py 

How to run the API and check it is up:

    python totalimpact/api.py
    curl -X GET http://127.0.0.1:5001/  # or use your web browser

For dev, how to run tests:

    apt-get install python-nose
    nosetests -v test/
    nosetests -v -A "not slow" test/    # avoids slow tests

Note also that running the API as above is the first stage in making it publicly available.
Follow-up should include checking that debug is set to False, then exposing the API via
a web server such as NGINX. Supervisord is recommended for keeping your processes up. 
There are lots of different ways to do this, so we will not go into detail.


# Notes for Mac

Deal with problems on OSX Snow Leopard:

1. Install [homebrew](http://mxcl.github.com/homebrew/).
2. Run `brew install -v couchdb` (The `-v` for "verbose" fixes a [weird bug](http://code418.com/blog/2012/02/22/couchdb-osx-lion-verbose/)). Install will take a while, as there are big dependencies.
3. Run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>

