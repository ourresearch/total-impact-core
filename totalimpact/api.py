#!/usr/bin/env python

from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
import os, json, time
from pprint import pprint

from totalimpact import dao
from totalimpact.models import Item, Collection, ItemFactory, CollectionFactory
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.tilogging import logging
from totalimpact import default_settings
import csv, StringIO


# set up logging
logger = logging.getLogger(__name__)



# set up the app
def create_app():
    app = Flask(__name__)
    configure_app(app)
    return app

def configure_app(app):
    app.config.from_object(default_settings)
    # parent directory
    here = os.path.dirname(os.path.abspath( __file__ ))
    # Check for config overrides
    if os.environ.has_key('TOTALIMPACT_CONFIG'):
        config_path = os.path.normpath(os.path.join(os.path.dirname(here), os.environ['TOTALIMPACT_CONFIG']))
        if os.path.exists(config_path):
            app.config.from_pyfile(config_path)
    else:
        config_path = os.path.join(os.path.dirname(here), 'app.cfg')
        if os.path.exists(config_path):
            app.config.from_pyfile(config_path)


app = create_app()

mydao = None

@app.before_request
def connect_to_db():
    '''sets up the db. this has to happen before every request, so that
    we can pass in alternate config values for testing'''
    global mydao
    mydao = dao.Dao(
        app.config["DB_NAME"],
        app.config["DB_URL"],
        app.config["DB_USERNAME"],
        app.config["DB_PASSWORD"]) 


# adding a simple route to confirm working API
@app.route('/')
def hello():
    msg = {
        "hello": "world",
        "message": "Congratulations! You have found the Total Impact API.",
        "moreinfo": "http://total-impact.tumblr.com/",
        "version": app.config["VERSION"]
    }
    resp = make_response( json.dumps(msg, sort_keys=True, indent=4), 200)        
    resp.mimetype = "application/json"
    return resp


'''
GET /tiid/:namespace/:id
404 if not found because not created yet
303 else list of tiids
'''
@app.route('/tiid/<ns>/<path:nid>', methods=['GET'])
def tiid(ns, nid):
    viewname = 'queues/by_alias'
    res = mydao.view(viewname)
    rows = res["rows"]
    tiids = [row["id"] for row in rows if row['key'] == [ns,nid]]

    if not tiids:
        abort(404)
    resp = make_response(json.dumps(tiids, sort_keys=True, indent=4 ), 303) 
    resp.mimetype = "application/json"
    return resp

def create_item(namespace, id):
    '''Utility function to keep DRY in single/multiple item creation endpoins'''
    item = ItemFactory.make_simple(mydao)
    item.aliases.add_alias(namespace, id)

    ## FIXME - see issue 86
    ## Should look up this namespace and id and see if we already have a tiid
    ## If so, return its tiid with a 200.
    # right now this makes a new item every time, creating many dupes

    # does not filter by whether we actually can process the namespace, since
    # we may be able to someday soon. It's user's job to not pass in junk.
    item.save()

    try:
        return item.id
    except AttributeError:
        abort(500)     


@app.route('/items', methods=['POST'])
def items_namespace_post():
    '''Creates multiple items based on a POSTed list of aliases.
    
    Note that this requires the POST content-type be sent as application/json..
    this could be seen as a bug or feature...'''

    # get aliases into tuples instead of lists so can hash into a set
    aliases_list = [(namespace, nid) for [namespace, nid] in request.json]
    logger.debug("In api /items with aliases " + str(aliases_list))

    unique_aliases = list(set(aliases_list))
    tiids = []
    for alias in unique_aliases:
        logger.debug("In api /items with alias " + str(alias))
        tiid = create_item(alias[0], alias[1])
        logger.debug("... created with tiid " + tiid)
        tiids.append(tiid)

    response_code = 201 # Created
    resp = make_response(json.dumps(tiids), response_code)
    resp.mimetype = "application/json"
    return resp

@app.route('/item/<namespace>/<path:id>', methods=['POST'])
def item_namespace_post(namespace, id):
    '''Creates a new item using the given namespace and id.

    POST /item/:namespace/:id
    201 location: {tiid}
    500?  if fails to create
    example /item/PMID/234234232
    '''
    tiid = create_item(namespace, id)
    response_code = 201 # Created
   
    resp = make_response(json.dumps(tiid), response_code)
    resp.mimetype = "application/json"
    return resp


'''GET /item/:tiid
404 if tiid not found in db
'''
@app.route('/item/<tiid>', methods=['GET'])
def item(tiid, format=None):
    # TODO check request headers for format as well.

    try:
        item_dict = ItemFactory.get_simple_item(mydao, tiid)
    except (LookupError, AttributeError):
        abort(404)

    if not item_dict:
        abort(404)
        
    resp = make_response(json.dumps(item_dict, sort_keys=True, indent=4))
    resp.mimetype = "application/json"
    return resp

'''
GET /items/:tiid,:tiid,...
returns a json list of item objects (100 max)
404 unless all tiids return items from db
'''
@app.route('/items/<tiids>', methods=['GET'])
@app.route('/items/<tiids>.<format>', methods=['GET'])
def items(tiids, format=None):
    items = []

    for index,tiid in enumerate(tiids.split(',')):
        if index > 99: break    # weak, change

        try:
            item_dict = ItemFactory.get_simple_item(mydao, tiid)
        except (LookupError, AttributeError):
            abort(404)

        if not item_dict:
            abort(404)

        items.append(item_dict)

    if format == "csv":
        # make the header
        csv = "tiid," + ','.join(sorted(items[0]['metrics'])) + "\n"
        for item in items:
            row = ''
            row = row + item["id"]
            for metric_name in sorted(item["metrics"]):
                row = row + ","
                try:
                    latest_key = sorted(
                        item['metrics'][metric_name]['values'],
                        reverse=True)[0]
                    val_to_add = item['metrics'][metric_name]['values'][latest_key]
                except IndexError:
                    val_to_add = ""

                row = row + str(val_to_add)

            csv =  csv + row + "\n"
            
        resp = make_response(csv[0:-2]) # remove trailing "\n"
        resp.mimetype = "text/csv"
        resp.headers.add("Content-Disposition", "attachment; filename=ti.csv")
    else:
        resp = make_response(json.dumps(items, sort_keys=True, indent=4))
        resp.mimetype = "application/json"

    return resp
        

@app.route('/provider', methods=['GET'])
def provider():

    ret = ProviderFactory.get_all_metadata()
    resp = make_response( json.dumps(ret, sort_keys=True, indent=4), 200 )
    resp.mimetype = "application/json"

    return resp


'''
GET /provider/:provider/memberitems?query=:querystring[&type=:type]
returns member ids associated with the group in a json list of (key, value) pairs like [(namespace1, id1), (namespace2, id2)] 
of type :type (when this needs disambiguating)
if > 100 memberitems, return the first 100 with a response code that indicates the list has been truncated
examples : /provider/github/memberitems?query=jasonpriem&type=github_user

POST /provider/:provider/aliases
alias object as cargo, may or may not have a tiid in it
returns alias object 

POST /provider/:provider
alias object as cargo, may or may not have tiid in it
returns dictionary with metrics object and biblio object
'''

# routes for providers (TI apps to get metrics from remote sources)
# external APIs should go to /item routes
# should return list of member ID {namespace:id} k/v pairs
# if > 100 memberitems, return 100 and response code indicates truncated
@app.route('/provider/<provider_name>/memberitems', methods=['GET'])
def provider_memberitems(provider_name):
    query = request.values.get('query','')

    logger.debug("In provider_memberitems with " + query)

    provider = ProviderFactory.get_provider(provider_name)
    logger.debug("provider: " + provider.provider_name)

    memberitems = provider.member_items(query, cache_enabled=False)
    
    resp = make_response( json.dumps(memberitems, sort_keys=True, indent=4), 200 )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/dryad/aliases/10.5061/dryad.7898
@app.route('/provider/<provider_name>/aliases/<path:id>', methods=['GET'] )
def provider_aliases(provider_name, id):

    provider = ProviderFactory.get_provider(provider_name)
    if id=="example":
        id = provider.example_id[1]
        url = "http://localhost:8080/" + provider_name + "/aliases?%s"
    else:
        url = None

    try:
        new_aliases = provider._get_aliases_for_id(id, url, cache_enabled=False)
    except NotImplementedError:
        new_aliases = []
        
    all_aliases = [(provider.example_id[0], id)] + new_aliases

    resp = make_response( json.dumps(all_aliases, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/dryad/metrics/10.5061/dryad.7898
@app.route('/provider/<provider_name>/metrics/<path:id>', methods=['GET'] )
def provider_metrics(provider_name, id):

    provider = ProviderFactory.get_provider(provider_name)
    if id=="example":
        id = provider.example_id[1]
        url = "http://localhost:8080/" + provider_name + "/metrics?%s"
    else:
        url = None

    metrics = provider.get_metrics_for_id(id, url, cache_enabled=False)

    resp = make_response( json.dumps(metrics, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/dryad/biblio/10.5061/dryad.7898
@app.route('/provider/<provider_name>/biblio/<path:id>', methods=['GET'] )
def provider_biblio(provider_name, id):

    provider = ProviderFactory.get_provider(provider_name)
    if id=="example":
        id = provider.example_id[1]
        url = "http://localhost:8080/" + provider_name + "/biblio?%s"
    else:
        url = None

    biblio = provider.get_biblio_for_id(id, url, cache_enabled=False)
    resp = make_response( json.dumps(biblio, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp


'''
GET /collection/:collection_ID
returns a collection object 

POST /collection
creates new collection
post payload a dict like:
    {
        items:[ [namespace, id],  [namespace, id], ...],
        title: "this is my title"
    }
returns collection_id
returns 405 or 201

PUT /collection/:collection
payload is a collection object
overwrites whatever was there before.
returns 404 or 200
(see http://stackoverflow.com/questions/2342579/http-status-code-for-update-and-delete)

# We don't want to support delete yet, too risky.  Taken out for now.
DELETE /collection/:collection
returns 404 or 204
(see http://stackoverflow.com/questions/2342579/http-status-code-for-update-and-delete)
'''
@app.route('/collection', methods = ['POST'])
@app.route('/collection/<cid>', methods = ['GET', 'PUT'])
def collection(cid=''):
    response_code = None

    try:
        coll = CollectionFactory.make(mydao, id=cid)
    except LookupError:
        coll = None

    if request.method == "POST":
        if coll:
            # Collection already exists: should call PUT instead
            abort(405)   # Method Not Allowed
        else:
            try:
                coll = CollectionFactory.make(mydao)
                coll.add_items(request.json["items"])
                coll.title = request.json["title"]
                coll.save()
                response_code = 201 # Created
            except (AttributeError, TypeError, JSONDecodeError):
                # we got missing or improperly formated data.
                # should log the error...
                abort(404)  #what is the right error message for 'needs arguments'?

    elif request.method == "PUT":
        # it exists in the database already, but we're going to overwrite it.
        #FIXME: currently does not delete anything...only adds. See #93
        if coll:
            coll = CollectionFactory.make(mydao, collection_dict=request.json )
            coll.save()
            response_code = 200 # OK
        else:
            abort(404)

    elif request.method == "DELETE":
        if coll:
            coll.delete()
            response_code = 204 # The server successfully processed the request, but is not returning any content
        else:
            abort(404)

    elif request.method == "GET":
        if coll:
            response_code = 200 #OK
        else:
            abort(404)

    resp = make_response( json.dumps( coll.as_dict(), sort_keys=True, indent=4 ), response_code)
    resp.mimetype = "application/json"
    return resp


if __name__ == "__main__":

    try:
        connect_to_db()
    except LookupError:
        print "CANNOT CONNECT TO DATABASE, maybe doesn't exist?"
        raise LookupError

    logger = logging.getLogger()

    # run it
    app.run(host='0.0.0.0', port=5001, debug=False)

