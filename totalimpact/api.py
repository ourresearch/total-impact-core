#!/usr/bin/env python

from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
import os, json, time

from totalimpact import dao
from totalimpact.models import Item, Collection, ItemFactory, CollectionFactory
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.tilogging import logging
from totalimpact import default_settings


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
metric_names = app.config["METRIC_NAMES"]

@app.before_request
def connect_to_db():
    '''sets up the db. this has to happen before every request, so that
    we can pass in alternate config values for testing'''
    global mydao #ick
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
    tiids = [row["id"] for row in rows]

    if not tiids:
        abort(404)
    resp = make_response( json.dumps(tiids, sort_keys=True, indent=4 ), 303) 
    resp.mimetype = "application/json"
    return resp

def create_item(namespace, id):
    '''Utility function to keep DRY in single/multiple item creation endpoins'''
    item = ItemFactory.make(mydao, metric_names)
    item.aliases.add_alias(namespace, id)

    ## FIXME - see issue 86
    ## Should look up this namespace and id and see if we already have a tiid
    ## If so, return its tiid with a 200.
    # right now this makes a new item every time, creating many dups

    # FIXME pull this from Aliases somehow?
    # check to make sure we know this namespace
    #known_namespace = namespace in Aliases().get_valid_namespaces() #implement
    known_namespaces = ["doi", "github", "url"]  # hack in the meantime
    if not namespace in known_namespaces:
        abort(501) # "Not Implemented"
    else:
        item.save() 

    try:
        return item.id
    except AttributeError:
        abort(500)     


@app.route('/items', methods=['POST'])
def items_namespace_post():
    '''Creates multiple items based on a POSTed list of aliases.
    
    Note that this requires the POST content-type be sent as application/json...
    this could be seen as a bug or feature...'''
    tiids = []
    for alias in request.json:
        tiid = create_item(alias[0], alias[1])
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



def make_item_dict(tiid):
    '''Utility function for /item and /items endpoints
    Will cause the request to abort with 404 if item is missing from db'''
    try:
        item = ItemFactory.get(mydao, id=tiid, metric_names=metric_names)
        item_dict = item.as_dict()
    except LookupError:
        abort(404)
    return item_dict

def make_item_resp(item_dict, format):
    if format == "html":
        try:
            template = item_dict["genre"] + ".html"
        except KeyError:
            template = "article.html"
            item_dict['genre'] = "article"
        resp = make_response(render_template(template, item=item_dict ))
        resp.content_type = "text/html"
    else:
        resp = make_response(json.dumps(item_dict, sort_keys=True, indent=4))
        resp.mimetype = "application/json"
    return resp

'''GET /item/:tiid
404 if tiid not found in db
'''
@app.route('/item/<tiid>', methods=['GET'])
@app.route('/item/<tiid>.<format>', methods=['GET'])
def item(tiid, format=None):
    # TODO check request headers for format as well.
    item_dict = make_item_dict(tiid)
    return make_item_resp(item_dict, format)

'''
GET /items/:tiid,:tiid,...
returns a json list of item objects (100 max)
404 unless all tiids return items from db
'''
@app.route('/items/<tiids>', methods=['GET'])
def items(tiids, format=None):
    items = []

    for index,tiid in enumerate(tiids.split(',')):
        if index > 99: break    # weak, change
        items.append(make_item_dict(tiid))

    resp = make_response(json.dumps(item_dict, sort_keys=True, indent=4))
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
@app.route('/provider/<pid>/memberitems', methods=['GET'])
def provider_memberitems(pid):
    query = request.values.get('query','')
    qtype = request.values.get('type','')

    logger.debug("In provider_memberitems with " + query + " " + qtype)

    provider = ProviderFactory.get_provider(app.config["PROVIDERS"][pid])
    logger.debug("provider: " + provider.provider_name)

    memberitems = provider.member_items(query, qtype)
    
    resp = make_response( json.dumps(memberitems, sort_keys=True, indent=4), 200 )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/Dryad/aliases/10.5061%2Fdryad.7898
@app.route('/provider/<pid>/aliases/<id>', methods=['GET'] )
def provider_aliases(pid,id):

    for prov in providers:
        if prov.id == pid:
            provider = prov
            break

    aliases = provider.get_aliases_for_id(id.replace("%", "/"))

    resp = make_response( json.dumps(aliases, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/Dryad/metrics/10.5061%2Fdryad.7898
@app.route('/provider/<pid>/metrics/<id>', methods=['GET'] )
def metric_snaps(pid,id):

    for prov in providers:
        if prov.id == pid:
            provider = prov
            break

    metrics = provider.get_metrics_for_id(id.replace("%", "/"))

    resp = make_response( json.dumps(metrics.data, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/Dryad/biblio/10.5061%2Fdryad.7898
@app.route('/provider/<pid>/biblio/<id>', methods=['GET'] )
def provider_biblio(pid,id):

    for prov in providers:
        if prov.id == pid:
            provider = prov
            break

    biblio = provider.get_biblio_for_id(id.replace("%", "/"))

    resp = make_response( json.dumps(biblio.data, sort_keys=True, indent=4) )
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

DELETE /collection/:collection
returns 404 or 204
(see http://stackoverflow.com/questions/2342579/http-status-code-for-update-and-delete)
'''
@app.route('/collection', methods = ['POST'])
@app.route('/collection/<cid>', methods = ['GET', 'PUT', 'DELETE'])
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
            except (AttributeError, TypeError): # missing or improperly formated data
                abort(404)  #what is the right error message for needs arguments?

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

    # Adding this by handle. fileConfig doesn't allow filters to be added
    from totalimpact.backend import ctxfilter
    handler = logging.handlers.RotatingFileHandler("logs/total-impact.log")
    handler.level = logging.DEBUG
    #formatter = logging.Formatter("%(asctime)s %(levelname)8s %(name)s %(item)s %(thread)s %(provider)s - %(message)s","%y%m%d %H%M%S")
    formatter = logging.Formatter("%(asctime)s %(levelname)8s %(item)8s %(thread)s%(provider)s - %(message)s","%y%m%d %H%M%S")
    handler.formatter = formatter
    handler.addFilter(ctxfilter)
    logger.addHandler(handler)
    ctxfilter.threadInit()

    logger.debug("test")

    from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
    from totalimpact.providers.provider import Provider, ProviderFactory

    # Start all of the backend processes
    print "Starting alias retrieval thread"
    providers = ProviderFactory.get_providers(app.config["PROVIDERS"])
    alias_thread = ProvidersAliasThread(providers, mydao)
    alias_thread.start()

    # Start each of the metric providers
    metrics_threads = []
    for provider in providers:
        thread = ProviderMetricsThread(provider, mydao)
        metrics_threads.append(thread)
        thread.start()

    # run it
    app.run(host='0.0.0.0', port=5001, debug=False)

    print "Stopping alias thread"
    alias_thread.stop()
    print "Stopping metric threads"
    for thread in metrics_threads:
        thread.stop()
    print "Waiting on metric threads"
    for thread in metrics_threads:
        thread.join()
    print "Waiting on alias thread"
    alias_thread.join()
    print "All stopped"


