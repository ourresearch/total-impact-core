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

How to install CouchDB to OSX Snow Leopard:

1. Install [homebrew](http://mxcl.github.com/homebrew/).
1. Run `brew install -v couchdb` (The `-v` for "verbose" fixes a [weird bug](http://code418.com/blog/2012/02/22/couchdb-osx-lion-verbose/)). Install will take a while, as there are big dependencies.
1. Run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>
