from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
from flaskext.login import login_user, current_user

import json
import totalimpact.util as util
import totalimpact.models
from totalimpact.core import app, login_manager

from totalimpact.config import Configuration
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)


# set config
config = Configuration()


# do account / auth stuff
@login_manager.user_loader
def load_account_for_login_manager(userid):
    out = totalimpact.models.User.get(userid)
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
        user = totalimpact.models.User.get(remote_user)
        if user:
            login_user(user, remember=False)
    elif 'api_key' in request.values:
        res = totalimpact.models.User.query(q='api_key:"' + request.values['api_key'] + '"')['hits']['hits']
        if len(res) == 1:
            user = totalimpact.models.User.get(res[0]['_source']['id'])
            if user:
                login_user(user, remember=False)

        
# static pages
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def content():
    return render_template('about.html')


# routes for items (TI scholarly object records)
@app.route('/item/<tiid>')
def item(tiid):
    item = totalimpact.models.Item.get(tiid)
    print item
    if item:
        item.set_last_requested()
        # is request for JSON or HTML
        # return relevant version of item
        resp = make_response(item.json)
        resp.mimetype = "application/json"
        return resp
    else:
        abort(404)

@app.route('/item/id/<namespace>/<nid>/')
def itemid(namespace,nid):
    if request.method == 'GET':
        # search for the item with this namespace and nid
        tiid = True
        if tiid:
            # send 303? do we redirect to the item or return its ID?
            return tiid
        else:
            abort(404)
    elif request.method == 'POST':
        item = totalimpact.models.Item()
        # do something to create the new item
        item.set_last_requested()
        tiid = item.save()
        if tiid:
            # set location header to /item/tiid
            abort(201)
        else:
            abort(500)

@app.route('/items/<tiids>')
def items(tiids):
    items = []
    for index,tiid in enumerate(tiids.split(',')):
        if index > 99: break
        thisitem = totalimpact.models.Item.get(tiid)
        if thisitem:
            thisitem.set_last_requested
            items.append( thisitem.data )
    resp = make_response( json.dumps(items, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

        
# routes for providers (TI apps to get metrics from remote sources)
# external APIs should go to /item routes
# should return list of member ID {namespace:id} k/v pairs
# if > 100 memberitems, return 100 and response code indicates truncated
# examples:
#    /provider/GitHub/memberitems?query=jasonpriem&type=profile
#    /provider/GitHub/memberitems?query=bioperl&type=orgs
#    /provider/Dryad/memberitems?query=Otto%2C%20Sarah%20P.&type=author
providers = ProviderFactory.get_providers(config)
@app.route('/provider/<pid>/memberitems')
def provider_memberitems(pid):
    query = request.values.get('query','')
    qtype = request.values.get('type','')

    logger.debug("In provider_memberitems with " + query + " " + qtype)
    
    for prov in providers:
        if prov.id == pid:
            provider = prov
            break

    logger.debug("provider: " + prov.id)

    memberitems = provider.member_items(query, qtype)
    
    # check for requested response type, or always JSON?
    resp = make_response( json.dumps(memberitems, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5000/provider/Dryad/aliases/10.5061%25dryad.7898
@app.route('/provider/<pid>/aliases/<id>', methods=['GET'] )
def provider_aliases(pid,id):
    for prov in providers:
        if prov.id == pid:
            provider = prov
            break
    aliases = provider.get_aliases_for_id(id.replace("%", "/"))
    # check for requested response type, or always JSON?
    resp = make_response( json.dumps(aliases, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5000/provider/Dryad/metrics/10.5061%25dryad.7898
@app.route('/provider/<pid>/metrics/<id>', methods=['GET'] )
def provider_metrics(pid,id):
    for prov in providers:
        if prov.id == pid:
            provider = prov
            break
    metrics = provider.get_metrics_for_id(id.replace("%", "/"))
    # check for requested response type, or always JSON?
    resp = make_response( json.dumps(metrics.data, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5000/provider/Dryad/biblio/10.5061%25dryad.7898
@app.route('/provider/<pid>/biblio/<id>', methods=['GET'] )
def provider_biblio(pid,id):
    for prov in providers:
        if prov.id == pid:
            provider = prov
            break
    biblio = provider.get_biblio_for_id(id.replace("%", "/"))
    # check for requested response type, or always JSON?
    resp = make_response( json.dumps(biblio.data, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# routes for collections 
# (groups of TI scholarly object items that are batched together for scoring)
@app.route('/collection', methods = ['GET','POST','PUT','DELETE'])
@app.route('/collection/<cid>/<tiid>')
def collection(cid='',tiid=''):

    if request.method == "GET":
        # check for requested response type, or always JSON?
        if cid:
            coll = totalimpact.models.Collection.get(cid)
            if coll:
                resp = make_response( coll.json )
                resp.mimetype = "application/json"
                return resp
            else:
                abort(404)
        else:
            abort(404)

    if request.method == "POST":
        if tiid:
            coll = totalimpact.models.Collection.get(cid)
            # TODO: update the list of tiids on this coll with this new one
            coll.save()
            resp = make_response( coll.json )
            resp.mimetype = "application/json"
            return resp
        elif not cid:
            # check if received object was json
            if request.json:
                idlist = request.json
            else:
                idlist = request.values.to_dict()
                for item in idlist:
                    try:
                        idlist[item] = json.loads(idlist[item])
                    except:
                        pass
            tiids = []
            for thing in idlist['list']:
                item = totalimpact.models.Item()
                item.aliases.add_alias(thing[0],thing[1])
                tiid = item.save()
                tiids.append(tiid)
                item.aliases.add_alias(namespace='tiid',id=tiid)
            coll = totalimpact.models.Collection(seed={'ids':tiids,'name':idlist['name']})
            resp = coll.save()
            return resp
        else:
            coll = totalimpact.models.Collection.get(cid)
            # TODO: merge the payload (a collection object) with the coll we already have
            # use richards merge stuff to merge hierarchically?
            coll.save()
            resp = make_response( coll.json )
            resp.mimetype = "application/json"
            return resp

    if request.method == "PUT":
        # check if received object was json
        coll = totalimpact.models.Collection()
        if request.json:
            coll.data = request.json
        else:
            coll.data = request.values.to_dict()
            for item in coll.data:
                try:
                    coll.data[item] = json.loads(coll.data[item])
                except:
                    pass
        coll.save()
        resp = make_response( coll.json )
        resp.mimetype = "application/json"
        return resp

    if request.method == "DELETE":
        if tiid:
            # remove tiid from tiid list on coll
            resp = "thing deleted"
            return resp
        elif cid:
            # delete the whole object
            coll = totalimpact.models.Collection.get(cid)
            deleted = coll.delete()
            abort(404)
        else:
            abort(404)


# routes for user stuff
@app.route('/user/<uid>')
def user(uid=''):
    if request.method == 'GET':
        user = totalimpact.models.User.get(uid)
        # check for requested response type, or always JSON?
        resp = make_response( json.dumps(user, sort_keys=True, indent=4) )
        resp.mimetype = "application/json"
        return resp

    # POST updated user data (but don't accept changes to the user colls list)    
    if request.method == 'POST':
        if uid:
            user = totalimpact.models.User.get(uid)
        else:
            user = totalimpact.models()
        if request.json:
            newdata = request.json
        else:
            newdata = request.values.to_dict()
            for item in newdata:
                try:
                    newdata[item] = json.loads(newdata[item])
                except:
                    pass
        if 'collection_ids' in newdata:
            del newdata['collection_ids']
        if 'password' in newdata:
            pass # should prob hash the password here (fix once user accounts exist)
        user.data.update(newdata)
        user.save()
        resp = make_response( user.json )
        resp.mimetype = "application/json"
        return resp
    
    # kill this user
    if request.method == 'DELETE':
        user = totalimpact.models.User.get(uid)
        user.delete()
        abort(404)

# /user/claim_collection/:collection_id
    # associates a given collection with the user; may require additional tokens, not sure yet.
# user/send_new_pw/:user_id
    # Sends new password to the email stored for that user.


if __name__ == "__main__":
    # try to prepare and connect to the database
    try:
        couch, db = totalimpact.dao.Dao.connection()
        print couch, db
    except:
        print "WARNING! No database available."

    # start the watchers
    # TODO: find out from rich where the watchers is...
    #totalimpact.watchers.init()
    #if not os.path.exists('watchers.pid'):
    #    watchers=subprocess.Popen(['python', 'totalimpact/watchers.py'])
    #    open('watchers.pid', 'w').write('%s' % watchers.pid)

    # run it
    app.run(host='0.0.0.0', debug=True)

    # remove unnecessary PIDs
    #if os.path.exists('watchers.pid'):
    #    os.remove('watchers.pid')
