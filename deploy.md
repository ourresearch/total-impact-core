# Deployment

(This was copied over from another project, still needs editing and check with TI)


## Pre-requisites

This is an example of deploying total impact

These instructions work on an ubuntu / debian machine, and explain how to get a
stable deployment using:

 * git (to get latest copy of code)
 * nginx (the web server that proxies to the web app)
 * python2.7+, pip, virtualenv (required to run the app)
 * gunicorn (runs the web app that receives the proxy from nginx)
 * supervisord (keeps everything up and running)


## nginx config

Create an nginx site config named e.g. ti.org
default location is /etc/nginx/sites-available
then symlink from /etc/nginx/sites-enabled

    upstream ti_server {
	    server 127.0.0.1:5050 fail_timeout=0;
    }

    server {
	    server_name  total-impact.org;

	    access_log  /var/log/nginx/total-impact.org.access.log;

	    server_name_in_redirect  off;

	    client_max_body_size 20M;

	    location / {
		    ## straight-forward proxy
		    proxy_redirect off;
	      	proxy_connect_timeout 75s;
	      	proxy_read_timeout 180s;
		    proxy_set_header Host $host;
		    proxy_set_header X-Real-IP $remote_addr;
		    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

		    proxy_pass   http://ti_server;
	    }
    }


## supervisord config

Create a supervisord config named e.g. ti.conf
- the default location for this is /etc/supervisor/conf.d

    [program:ti.org]
    command=/home/USERNAME/ti.org/bin/gunicorn -w 4 -b 127.0.0.1:5050 totalimpact.api:app
    user=www-data
    directory=/home/USERNAME/ti.org/src/total-impact-core
    stdout_logfile=/var/log/supervisor/ti.org-access.log
    stderr_logfile=/var/log/supervisor/ti.org-error.log
    autostart=true


## Install TI

Create a virtualenv and get the latest TI code installed.
make sure the right python version is available on your system, 
then start a virtualenv to run it in

    cd /home/USERNAME
    virtualenv -p python2.7 ti.org --no-site-packages
    cd ti.org
    mkdir src
    cd bin
    source activate
    cd ../src
    git clone https://github.com/total-impact/total-impact-core
    cd total-impact-core
    python setup.py install


If problems with this install, try a dev install

    pip install -e .


Then install gunicorn into the virtualenv

    pip install gunicorn


Now set any local config variables you require


## Enable everything

    cd /etc/nginx/sites-enabled
    ln -s ../sites-available/ti.org .
    /etc/init.d/nginx reload
    supervisorctl reread
    supervisorctl update


Configure your domain name to point at your server, and it should work.


