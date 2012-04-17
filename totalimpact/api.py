from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
import os, json, time

from totalimpact import dao
from totalimpact.models import Item, Collection, Metrics, ItemFactory, CollectionFactory
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
    config_path = os.path.join(os.path.dirname(here), 'app.cfg')
    if os.path.exists(config_path):
        app.config.from_pyfile(config_path)

app = create_app()
mydao = dao.Dao(app.config["DB_NAME"])
providers = ProviderFactory.get_providers(app.config["PROVIDERS"])

@app.before_request
def connect_to_db():
    try:
        ## FIXME add a check to to make sure it has views already.  If not, reset
        #mydao.delete_db(db_name)

        ## FIXME move this back into the dao. no need for non-db classes to have
        # to think about this.

        if not mydao.db_exists(app.config["DB_NAME"]):
            mydao.create_db(app.config["DB_NAME"])
        mydao.connect_db(app.config["DB_NAME"])
    except LookupError:
        print "CANNOT CONNECT TO DATABASE, maybe doesn't exist?"
        raise LookupError

# adding a simple route to confirm working API
@app.route('/')
def hello():
    msg = {
        "hello": "world",
        "message": "Congratulations! You have found the Total Impact API.",
        "moreinfo": "http://total-impact.tumblr.com/",
        "version": app.config["version"]
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


@app.route('/item/<namespace>/<path:nid>', methods=['POST'])
def item_namespace_post(namespace, nid):
    '''Creates a new item using the given namespace and id.

    POST /item/:namespace/:id
    201 location: {tiid}
    500?  if fails to create
    example /item/PMID/234234232
    '''
    
    item = ItemFactory.make(mydao)
    item.aliases.add_alias(namespace, nid)

    ## FIXME - see issue 86
    ## Should look up this namespace and id and see if we already have a tiid
    ## If so, return its tiid with a 200.
    # right now this makes a new item every time, creating many dups

    # FIXME pull this from Aliases somehow?
    # check to make sure we know this namespace
    #known_namespace = namespace in Aliases().get_valid_namespaces() #implement
    known_namespaces = ["doi", "github"]  # hack in the meantime
    if not namespace in known_namespaces:
        abort(501) # "Not Implemented"
    else:
        item.save()
        response_code = 201 # Created

        if not item.id:
            abort(500)
        resp = make_response(json.dumps(item.id), response_code)
        resp.mimetype = "application/json"
        return resp


'''
GET /item/:tiid
404 if no tiid else structured item

GET /items/:tiid,:tiid,...
returns a json list of item objects (100 max)
'''
@app.route('/item/<tiids>', methods=['GET'])
@app.route('/items/<tiids>', methods=['GET'])
def items(tiids):
    items = []
    for index,tiid in enumerate(tiids.split(',')):
        if index > 99: break    # weak

        try:
            item = ItemFactory.make(mydao, id=tiid)
            item.last_requested = time.time()
            items.append( item.as_dict() )
        except LookupError:
            # TODO: is it worth setting this blank? or do nothing?
            # if do nothing, returned list length will not match supplied list length
            items.append( {} )

    if len(items) == 1 and not request.path.startswith('/items/') :
        items = items[0]

    if items:
        resp = make_response( json.dumps(item.as_dict(), sort_keys=True, indent=4) )
        resp.mimetype = "application/json"
        return resp
    else:
        abort(404)


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
    
    for prov in providers:
        if prov.id == pid:
            provider = prov
            break

    logger.debug("provider: " + prov.id)

    memberitems = provider.member_items(query, qtype)
    
    resp = make_response( json.dumps(memberitems, sort_keys=True, indent=4), 200 )
    resp.mimetype = "application/json"
    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5000/provider/Dryad/aliases/10.5061%2Fdryad.7898
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
# Example: http://127.0.0.1:5000/provider/Dryad/metrics/10.5061%2Fdryad.7898
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
# Example: http://127.0.0.1:5000/provider/Dryad/biblio/10.5061%2Fdryad.7898
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
post payload is a list of item IDs as [namespace, id]
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
            if not request.json:
                abort(404)  #what is the right error message for needs arguments?
            coll = CollectionFactory.make(mydao)
            coll.add_items(request.json)
            coll.save()
            response_code = 201 # Created

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

    # run it
    app.run(host='0.0.0.0', debug=True)



