This is the latest version of Total Impact, 
the software that runs the service available at http://total-impact.org

This is totally scratch right now - it is an in-progress port from 
PHP. This README and other content will be updated very soon.

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

