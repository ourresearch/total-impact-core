installation and use
==================

You need Python 2.7, because Heroku is 2.7. This is a bit of a pain, but as long as you remember to run everything in the virtualenv, you’re ok.

If you get KeyErrors and totalimpact won’t import, you haven’t exported the env variables correctly.
installation procedure. Here are the steps:

installation
============

## global stuff

### install heroku toolbelt 

(see https://toolbelt.heroku.com/ for instructions)

### add ssh key

    heroku keys:add ~/.ssh/id_rsa.pub # (or path to your public key, ex: heroku keys:add ~/.ssh/github_rsa.pub)

### Install python dependencies

    sudo apt-get install python-virtualenv
    sudo apt-get install python2.7 # use the dmg installer on OSX instead

### Install extra libs to run lxml

    sudo apt-get install libxml2-dev
    sudo apt-get install libxslt1-dev 
    sudo apt-get install python2.7-dev

### Clone the repos

    git clone git://github.com/total-impact/total-impact-core
    git clone git://github.com/total-impact/total-impact-webapp

### paste env vars into .bashrc 

    sudo nano ~/.bashrc

#### these are for total-impact-core:

    export MENDELEY_KEY= key
    export PLOS_KEY= key
    export SLIDESHARE_KEY= key
    export SLIDESHARE_SECRET= key
    export TOPSY_KEY=key
    export LOG_LEVEL=debug
    export CLOUDANT_URL=key # or to run locally: CLOUDANT_URL=http://localhost:5984)
    export CLOUDANT_DB=ti

#### these are for total-impact-webapp:

    export API_ROOT=localhost:5001 # production: total-impact-core.herokuapp.com

### this is so you can see the stdout logs [when you run foreman](http://www.google.com/url?q=https%3A%2F%2Fgithub.com%2Fddollar%2Fforeman%2Fwiki%2FMissing-Output&sa=D&sntz=1&usg=AFQjCNELDU4lGGgu4FqSSvMYWr_3tiFegg)

    export PYTHONUNBUFFERED=true

## do for total-impact-core and again for total-impact-webapp:

    cd total-impact-core

### Setup the virtualenv

    virtualenv --distribute -p /usr/bin/python2.7 venv 

### Add the heroku repo; from [StackOverflow thread](http://www.google.com/url?q=http%3A%2F%2Fstackoverflow.com%2Fquestions%2F5129598%2Fhow-to-link-a-folder-with-an-existing-heroku-app&sa=D&sntz=1&usg=AFQjCNG8ifFsW5WlYrXCSeuHxgniHY-sqA).

    git remote add heroku git@heroku.com:total-impact-core.git
    git remote add staging git@heroku.com:total-impact-core-staging.git

### install
    pip install -r requirements.txt -e .


use
===


### running with flask webserver (nicer debugging environment)

    # need three terminals:
    cd total-impact-core
    source venv/bin/activate
    python run.py

    cd total-impact-core
    source venv/bin/activate
    python totalimpact/backend.py

    cd total-impact-webapp
    source venv/bin/activate
    python run.py

### running in foreman

    foreman start --port 5000
    foreman start --port 5001

### running using the staging server

    heroku config:add API_ROOT=api.total-impact-core-staging.herokuapp.com --remote staging
    heroku ps:scale web=1 worker=1 --remote staging
    # don’t forget to spin down the staging server when you’re done: 
    heroku ps:scale web=0 worker=0 --remote staging


deploying to heroku
===================

    git push heroku master 
    # or: git push staging master
    # or: git push newfeaturebranch staging:master

### view heroku logs

    heroku logs --tail --remote staging # or --remote heroku


first-time installation
-----------------------

This shouldn’t ever need to be done again, but just in case...

### Create Heroku configs if necessary

    # See the env vars above. here's one example:
    heroku config:add LOG_LEVEL=debug # or --remote heroku

### Add or remove workers

    cd total-impact-core
    heroku ps:scale web=1 worker=1 # or --remote heroku

