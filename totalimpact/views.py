
from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
import os, json, time, datetime
from pprint import pprint

from totalimpact import dao, app
from totalimpact.models import Item, Collection, ItemFactory, CollectionFactory
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact import default_settings
import csv, StringIO, logging

logger = logging.getLogger("ti.views")

@app.before_request
def connect_to_db():
    '''sets up the db. this has to happen before every request, so that
    we can pass in alternate config values for testing'''
    global mydao
    mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.environ["CLOUDANT_DB"])

#@app.before_request
def check_api_key():
    ti_api_key = request.values.get('api_key','')
    logger.debug("In check_api_key with " + ti_api_key)
    if not ti_api_key:
        response = make_response("please get an api key and include api_key=YOURKEY in your query", 403)
        return response

@app.after_request
def add_crossdomain_header(resp):
    resp.headers['Access-Control-Allow-Origin'] = "*"
    resp.headers['Access-Control-Allow-Headers'] = "Content-Type"
    return resp

# adding a simple route to confirm working API
@app.route('/')
@app.route('/v1')
def hello():
    msg = {
        "hello": "world",
        "message": "Congratulations! You have found the total-Impact API.",
        "moreinfo": "http://total-impact.tumblr.com/",
        "contact": "totalimpactdev@gmail.com",
        "version": app.config["VERSION"]
    }
    resp = make_response( json.dumps(msg, sort_keys=True, indent=4), 200)        
    resp.mimetype = "application/json"
    return resp

def get_tiid_by_alias(ns, nid):
    res = mydao.view('queues/by_alias')

    matches = res[[ns,nid]] # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
        
    if matches.rows:
        if (len(matches.rows) > 1):
            logger.warning("More than one tiid for alias (%s, %s)" %(ns, nid))
        tiid = matches.rows[0]["id"]
    else:
        tiid = None
    return tiid

'''
GET /tiid/:namespace/:id
404 if not found because not created yet
303 else list of tiids
'''
@app.route('/tiid/<ns>/<path:nid>', methods=['GET'])
def tiid(ns, nid):
    tiid = get_tiid_by_alias(ns, nid)

    if not tiid:
        abort(404)
    resp = make_response(json.dumps(tiid, sort_keys=True, indent=4 ), 303) 
    resp.mimetype = "application/json"
    return resp

def create_item(namespace, nid):
    logger.debug("In create_item with alias" + str((namespace, nid)))
    item = ItemFactory.make_simple(mydao)
    item.aliases.add_alias(namespace, nid)
    item.needs_aliases = datetime.datetime.now().isoformat()
    item.save()

    try:
        return item.id
    except AttributeError:
        abort(500)     

def update_item(tiid):
    logger.debug("In update_item with tiid " + tiid)
    item_doc = mydao.get(tiid)

    # set the needs_aliases timestamp so it will go on queue for update
    #item = ItemFactory.get_item_object_from_item_doc(mydao, item_doc)
    item_doc["needs_aliases"] = datetime.datetime.now().isoformat()
    item_doc["id"] = item_doc["_id"]
    mydao.save(item_doc)

    try:
        return tiid
    except AttributeError:
        abort(500)     


def items_tiid_post(tiids):
    logger.debug("In api /items with tiids " + str(tiids))

    updated_tiids = []
    for tiid in tiids:
        updated_tiid = update_item(tiid)
        updated_tiids.append(updated_tiid)

    response_code = 200
    resp = make_response(json.dumps(updated_tiids), response_code)
    resp.mimetype = "application/json"
    return resp

@app.route('/items', methods=['POST'])
def items_namespace_post():
    try:
        aliases_list = [(namespace, nid) for [namespace, nid] in request.json]
    except ValueError:
        #is a list of tidds, so do update instead
        return items_tiid_post(request.json)

    # no error, so do lookups and create the ones that don't exist
    logger.debug("In api /items with aliases " + str(aliases_list))

    unique_aliases = list(set(aliases_list))
    tiids = []
    for alias in unique_aliases:
        (namespace, nid) = alias
        logger.debug("In api /items with alias " + str(alias))
        existing_tiid = get_tiid_by_alias(namespace, nid)
        if existing_tiid:
            tiid = existing_tiid
            logger.debug("... found with tiid " + tiid)
        else:
            tiid = create_item(namespace, nid)
            logger.debug("... created with tiid " + tiid)
        tiids.append(tiid)

    response_code = 201 # Created
    resp = make_response(json.dumps(tiids), response_code)
    resp.mimetype = "application/json"

    return resp

@app.route('/item/<namespace>/<path:nid>', methods=['POST'])
def item_namespace_post(namespace, nid):
    '''Creates a new item using the given namespace and id.

    POST /item/:namespace/:nid
    201 location: {tiid}
    500?  if fails to create
    example /item/PMID/234234232
    '''
    tiid = get_tiid_by_alias(namespace, nid)
    if tiid:
        logger.debug("... found with tiid " + tiid)
    else:
        tiid = create_item(namespace, nid)
        logger.debug("... created with tiid " + tiid)

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

def make_csv_rows(items):
    header_metric_names = []
    for item in items:
        header_metric_names += item["metrics"].keys()

    # get unique
    header_alias_names = ["title", "doi"]
    header_metric_names = sorted(list(set(header_metric_names)))

    # make header row
    csv_list = ["tiid," + ','.join(header_alias_names + header_metric_names)]

    # body rows
    for item in items:
        column_list = [item["id"]]
        for alias_name in header_alias_names:
            try:
                value = item['aliases'][alias_name][0]
                if (" " in value) or ("," in value):
                    value = '"' + value + '"'
                column_list += [value]
            except (IndexError, KeyError):
                column_list += [""]        
        for metric_name in header_metric_names:
            try:
                values = item['metrics'][metric_name]['values']
                latest_key = sorted(values, reverse=True)[0]
                column_list += [str(values[latest_key])]
            except (IndexError, KeyError):
                column_list += [""]
        print column_list
        csv_list.append(",".join(column_list))

    # join together in a string
    csv = "\n".join(csv_list)
    return csv

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
        if index > 500: break    # weak, change

        try:
            item_dict = ItemFactory.get_simple_item(mydao, tiid)
        except (LookupError, AttributeError):
            abort(404)

        if not item_dict:
            abort(404)

        items.append(item_dict)

    if format == "csv":
        csv = make_csv_rows(items)
        resp = make_response(csv)
        resp.mimetype = "text/csv"
        resp.headers.add("Content-Disposition", "attachment; filename=ti.csv")
    else:
        resp = make_response(json.dumps(items, sort_keys=True, indent=4))
        resp.mimetype = "application/json"

    resp.headers['Access-Control-Allow-Origin'] = "*"
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
    resp.headers['Access-Control-Allow-Origin'] = "*"

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


