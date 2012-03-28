This is the latest version of total-impact, the software that runs the service available at http://total-impact.org

This isn't the deployed version -- it is an in-progress port the old codebase at http://github.com/mhahnel/Total-Impact
This README will be updated when this is the deployed version.

# About total-impact

See [http://total-impact/about](http://total-impact/about).

# Install and run total-impact

## Get total-impact code

How to install for dev:

    pip install -e .

How to install:

    python setup.py install

How to run tests:

    nosetests -v test/
    nosetests -v -A "not slow" test/

How to run the web app:

    cd total-impact
    python totalimpact/web.py
    then surf up http://127.0.0.1:5000/

## Install and run CouchDB

Total-impact needs a running instance of CouchDB.

To install on Ubuntu Linux:  

1. apt-get install couchdb
1. run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>

To install on OSX Snow Leopard:

1. Install [homebrew](http://mxcl.github.com/homebrew/).
1. Run `brew install -v couchdb` (The `-v` for "verbose" fixes a [weird bug](http://code418.com/blog/2012/02/22/couchdb-osx-lion-verbose/)). Install will take a while, as there are big dependencies.
1. Run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>


## Configure CouchDB for total-impact

Customized settings for connecting to CouchDB can be set in the config/totalimpact.conf.json file.

By default, total-impact will try to contact CouchDB at http://localhost:5984/ through an admin user called "test" with password "password".

To configure CouchDB for this default admin account, make sure your couch config file (often at /usr/local/etc/couchdb/local.ini) contains these lines:

    [admins]
    test = password

then restart couchdb (the password will be overwritten in the local.ini file with a hash of the password).

When total-impact starts, it will, if necessary, create the database and all necessary views 
(you can see the view definitions [in the config](https://github.com/total-impact/total-impact/blob/master/config/totalimpact.conf.json).


