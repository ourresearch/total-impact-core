from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
from flaskext.login import login_user, current_user

import json
import totalimpact.util as util
import totalimpact.models
from totalimpact.core import app, login_manager

from totalimpact.config import Configuration
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError


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


@app.route('/about/')
def content():
    return render_template('about.html')


# routes for items (TI scholarly object records)
@app.route('/item/<tiid>')
def item(tiid):
    item = totalimpact.models.Item.get(tiid)
    if item:
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
        items.append( totalimpact.models.Item.get(tiid).data )
    resp = make_response( json.dumps(items, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

        
# routes for providers (TI apps to get metrics from remote sources)
# external APIs should go to /item routes
# should return list of member ID {namespace:id} k/v pairs
# if > 100 memberitems, return 100 and response code indicates truncated
# examples:
#    /provider/GitHub/memberitems?query=jasonpriem&type=user
#    /provider/GitHub/memberitems?query=bioperl&type=org
#    /provider/Dryad/memberitems?query=Otto%2C%20Sarah%20P.
config = Configuration('config/totalimpact.conf.json')
providers = ProviderFactory.get_providers(config)
@app.route('/provider/<pid>/memberitems')
def provider_memberitems(pid):
    query = request.values.get('query','')
    qtype = request.values.get('type','')
    
    for prov in providers:
        if prov.id == pid:
            provider = prov
            break

    # FIXME: how does provider take the type, if there is one?
    memberitems = provider.member_items(query)
    
    # check for requested response type, or always JSON?
    resp = make_response( json.dumps(memberitems, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

@app.route('/provider/<pid>/<aliases>', methods=['POST'] )
def provider_aliases(pid,aliases=''):
    # these two will be implemented internally but not exposed via REST:
    if aliases:
        # alias object as cargo, may or may not have a tiid in it
        # returns alias object
        return "alias object"
    else:
        #alias object as cargo, may or may not have tiid in it
        #returns dictionary with metrics object and biblio object
        return "metrics and biblio objs dict"


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
            # update the list of tiids on this coll with this new one
            resp = "something like updated"
            return resp
        elif not cid:
            # check if received object was json
            if request.json:
                idlist = request.json
            else:
                idlist = json.loads(request.data)
            tiids = []
            for thing in idlist:
                item = totalimpact.models.Item()
                item.aliases.add_alias(namespace=thing[0],id=thing[1])
                tiid = item.save()
                tiids.append(tiid)
                item.aliases.add_alias(namespace='tiid',id=tiid)
            coll = totalimpact.models.Collection(seed={ids:tiids})
            resp = coll.save()
            return resp
        else:
            # merge the payload (a collection object) with the coll we already have
            # use richards merge stuff to merge hierarchically?
            resp = "something like updated"
            return resp

    if request.method == "PUT":
        # check if received object was json
        coll = totalimpact.models.Collection()
        if request.json:
            coll.data = request.json
        else:
            coll.data = json.loads(request.data)
        coll.save()
        resp = 201
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
            if deleted:
                abort(404)
            else:
                return "err.."
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
        pass
    
    # kill this user
    if request.method == 'DELETE':
        user = totalimpact.models.User.get(uid)
        user.delete()
        return 'killed' # should return 404?

# /user/claim_collection/:collection_id
    # associates a given collection with the user; may require additional tokens, not sure yet.
# user/send_new_pw/:user_id
    # Sends new password to the email stored for that user.


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

