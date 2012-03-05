from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
from flaskext.login import login_user, current_user

import totalimpact.util as util
import totalimpact.dao
from totalimpact.core import app, login_manager


# do account / auth stuff
@login_manager.user_loader
def load_account_for_login_manager(userid):
    out = totalimpact.dao.Account.get(userid)
    return out

@app.context_processor
def set_current_user():
    """ Set some template context globals. """
    return dict(current_user=current_user)

@app.before_request
def standard_authentication():
    """Check remote_user on a per-request basis."""
    remote_user = request.headers.get('REMOTE_USER', '')
    if remote_user:
        user = totalimpact.dao.Account.get(remote_user)
        if user:
            login_user(user, remember=False)
    elif 'api_key' in request.values:
        res = totalimpact.dao.Account.query(q='api_key:"' + request.values['api_key'] + '"')['hits']['hits']
        if len(res) == 1:
            user = totalimpact.dao.Account.get(res[0]['_source']['id'])
            if user:
                login_user(user, remember=False)

        
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def content():
    return render_template('about.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

