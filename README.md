This is the latest version of total-impact, the software that runs the service available at http://total-impact.org

This isn't the deployed version -- it is an in-progress port the old codebase at http://github.com/mhahnel/Total-Impact
This README will be updated when this is the deployed version

How to install for dev:

    pip install -e .

How to install:

    python setup.py install

How to run tests:

    nosetests -v test/

How to run the web app:

    cd total-impact
    python totalimpact/web.py
    then surf up http://127.0.0.1:5000/

Note that you need CouchDB installed so that Total Impact can talk to it. 
Settings for your CouchDB should be added to the config/totalimpact.conf.json file.
On startup, TI will try to talk to the database and create the necessary views 
(you can see the view definitions in the config too.)

How to install CouchDB on Ubuntu Linux:

It is available in the recent repos

    apt-get install couchdb

How to install CouchDB to OSX Snow Leopard:

1. Install [homebrew](http://mxcl.github.com/homebrew/).
1. Run `brew install -v couchdb` (The `-v` for "verbose" fixes a [weird bug](http://code418.com/blog/2012/02/22/couchdb-osx-lion-verbose/)). Install will take a while, as there are big dependencies.
1. Run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>

To get CouchDB ready for use in the app, you need to create a database called "ti".  One way to do this is in python:

    import couchdb
    couch = couchdb.Server('http://localhost:5984/')   # assumes server is running via `couchdb` at the command line
    db = couch.create("ti") 
    
    
