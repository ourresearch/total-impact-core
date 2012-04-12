# About

This is the latest version of total-impact-core. Installing this provides the 
backend and API for the total-impact service. You can then build or run a 
frontend or consume direct from the API into your own frontend.

(Our own frontend is available at [http://github.com/total-impact/total-impact-webapp](http://github.com/total-impact/total-impact-webapp).)

This isn't the deployed version -- it is an in-progress port the old codebase 
at http://github.com/mhahnel/Total-Impact

The deployed version is available at [http://total-impact.org](http://total-impact.org), 
and see [http://total-impact.org/about](http://total-impact.org/about) for more info.


# Install

This assumes you are running on a debian / Ubuntu based server.

Get total-impact-core code by cloning from this repo and cd into the directory.
There are various ways to get code from the repo, here is one example.

    git clone https://github.com/total-impact/total-impact-core
    cd total-impact-core

How to install for dev:

    pip install -e .

Or to install:

    python setup.py install

How to run tests (requires nosetests):

    nosetests -v test/
    nosetests -v -A "not slow" test/    # avoids slow tests

How to run and check the api:

    python totalimpact/api.py
    curl -X GET http://127.0.0.1:5000/  # or use your web browser


# Dependencies

Total Impact needs lxml and memcache, and a running instance of CouchDB

    apt-get install python-lxml
    apt-get install memcached
    apt-get install couchdb

    # check couch is up
    curl -X GET http://localhost:5984   # or use your web browser


# Notes for OSX Snow Leopard:

1. Install [homebrew](http://mxcl.github.com/homebrew/).
2. Run `brew install -v couchdb` (The `-v` for "verbose" fixes a [weird bug](http://code418.com/blog/2012/02/22/couchdb-osx-lion-verbose/)). Install will take a while, as there are big dependencies.
3. Run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>


# Config

Customized settings can be set in the config/totalimpact.conf.json file.

By default, total-impact will try to contact CouchDB at http://localhost:5984/ through an admin user called "test" with password "password". To configure CouchDB for this default just use the Futon admin client at <http://localhost:5984/_utils>. At the bottom-right, click "Add User," and add user called "test" with the password "password".

When total-impact starts, it will, if necessary, create the database and all necessary views 
(you can see the view definitions [in the config](https://github.com/total-impact/total-impact/blob/master/config/totalimpact.conf.json).

Note also that running the API as above is the first stage in making it publicly available.
Follow-up should include checking that debug is set to False, then exposing the API via
a web server such as NGINX. Supervisord is recommended for keeping your processes up. 



