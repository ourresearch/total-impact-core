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

