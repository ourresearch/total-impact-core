
from flask import json, request, redirect, abort, make_response
from flask import render_template
import os, datetime, redis

from totalimpact import dao, app
from totalimpact.models import ItemFactory, CollectionFactory
from totalimpact.providers.provider import ProviderFactory
from totalimpact import default_settings
import logging

logger = logging.getLogger("ti.views")
logger.setLevel(logging.DEBUG)
redis = redis.from_url(os.getenv("REDISTOGO_URL"))

mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.getenv("CLOUDANT_DB"))

def set_db(url, db):
    """useful for unit testing, where you want to use a local database
    """
    global mydao
    mydao = dao.Dao(url, db)
    return mydao


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
    item = ItemFactory.make()
    
    # set this so we know when it's still updating later on
    mydao.set_num_providers_left(
        item["_id"],
        ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
    )


    item["aliases"][namespace] = [nid]
    item["needs_aliases"] = datetime.datetime.now().isoformat()
    
    mydao.save(item)
    logger.info("Created new item '{id}' with alias '{alias}'".format(
        id=item["_id"],
        alias=str((namespace, nid))
    ))

    try:
        return item["_id"]
    except AttributeError:
        abort(500)    

def update_item(tiid):
    logger.debug("In update_item with tiid " + tiid)
    item_doc = mydao.get(tiid)

    # set the needs_aliases timestamp so it will go on queue for update
    item_doc["needs_aliases"] = datetime.datetime.now().isoformat()

    # set this so we know when it's still updating later on
    mydao.set_num_providers_left(
        item_doc["_id"],
        ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
    )
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
def items_post():
    """
    Depending on input, updates, retrieves, or creates a set of items

    If input is a list of tiids, it updates them.
    If input is a list of aliases,
        If we've already got a tiid for this alias, it get it.
        If it's a new alias, it makes a new item for it.

    In all cases, returns a list of tiids.
    Could use much refactoring, as much code is replicated between this and /item.
    Even better, most of this should move into a Collection or Updater model.
    """
    logger.debug("POST/items got this json: " + str(request.json))
    if isinstance(request.json[0], basestring):
        tiids = request.json
        
        # this seems to be a list of tiids; we'll do an update
        logger.info("POST /items got a list of tiids; doing an update.")
        logger.debug("POST /items got this list of tiids; doing an update with them: {tiids_str}".format(
            tiids_str=str(tiids)
        ))

        updated_tiids = []
        for tiid in request.json:
            updated_tiid = update_item(tiid)
            updated_tiids.append(updated_tiid)

        response_code = 200
        tiids = updated_tiids
    else:
        # we got some alias tuples; time to create new items.
        logger.info("POST /items got a list of aliases; creating new items for 'em.")
        logger.debug("POST /items got this list of aliases; creating new items for 'em: {aliases}".format(
            aliases=str(request.json)
        ))
        try:
            aliases_list = [(namespace, nid) for [namespace, nid] in request.json]
        except ValueError:
            logger.error("bad input to POST /items (requires tiids or [namespace, id] pairs):{input}".format(
                input=str(request.json)
            ))
            abort(404, "POST /items requires a list of either tiids or [namespace, id] pairs.")

        tiids = []
        items = []
        aliases_list = [(namespace.strip(), nid.strip()) for (namespace, nid) in aliases_list]
        for alias in aliases_list:
            (namespace, nid) = alias
            existing_tiid = get_tiid_by_alias(namespace, nid)
            if existing_tiid:
                tiids.append(existing_tiid)
                logger.debug("POST /items found an existing tiid ({tiid}) for alias {alias}".format(
                    tiid=existing_tiid,
                    alias=str(alias)
                ))
            else:
                logger.debug("POST /items: alias {alias} isn't in the db; making a new item for it.".format(
                    alias=alias
                ))
                item = ItemFactory.make()
                item["aliases"][namespace] = [nid]
                item["needs_aliases"] = datetime.datetime.now().isoformat()
                items.append(item)
                tiids.append(item["_id"])

        logger.debug("POST /items saving a group of {num} new items.".format(
            num=len(items)
        ))
        logger.debug("POST /items saving a group of {num} new items: {items}".format(
            num=len(items),
            items=str(items)
        ))

        # for each item, set the number of providers that need to run before the update is done
        for item in items:
            mydao.set_num_providers_left(
                item["_id"],
                ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
            )

        # batch upload the new docs to the db
        for doc in mydao.db.update(items):
            pass

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
        logger.debug("new item created with tiid " + tiid)

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
        item = ItemFactory.get_item(mydao, tiid)
    except (LookupError, AttributeError):
        abort(404)

    if not item:
        abort(404)
    
    if mydao.get_num_providers_left(tiid) > 0:
        response_code = 210 # not complete yet
        item["currently_updating"] = True
    else:
        response_code = 200
        item["currently_updating"] = False

    resp = make_response(json.dumps(item, sort_keys=True, indent=4), response_code)
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
        print "keys: " + str(item.keys())
        column_list = [item["_id"]]
        for alias_name in header_alias_names:
            try:
                value_to_store = item['aliases'][alias_name][0]
                if (" " in value_to_store) or ("," in value_to_store):
                    value_to_store = '"' + value_to_store + '"'
                column_list += [value_to_store]
            except (IndexError, KeyError):
                column_list += [""]        
        for metric_name in header_metric_names:
            try:
                values = item['metrics'][metric_name]['values']
                latest_key = sorted(values, reverse=True)[0]
                value_to_store = str(values[latest_key])
                if (" " in value_to_store) or ("," in value_to_store):
                    value_to_store = '"' + value_to_store + '"'
                column_list += [value_to_store]
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

    something_currently_updating = False
    for index,tiid in enumerate(tiids.split(',')):
        if index > 500: break    # weak, change

        try:
            item = ItemFactory.get_item(mydao, tiid)
        except (LookupError, AttributeError), e:
            logger.warning("Got an error looking up tiid '{tiid}'; aborting with 404. error: {error}".format(
                tiid=tiid,
                error = e.__repr__()
            ))
            abort(404)

        if not item:
            logger.warning("Looks like there's no item with tiid '{tiid}': aborting with 404".format(
                tiid=tiid
            ))
            abort(404)

        currently_updating = mydao.get_num_providers_left(tiid) > 0
        item["currently_updating"] = currently_updating
        something_currently_updating = something_currently_updating or currently_updating

        items.append(item)

    # return success if all reporting is complete for all items    
    if something_currently_updating:
        response_code = 210 # not complete yet
    else:
        response_code = 200

    if format == "csv":
        csv = make_csv_rows(items)
        resp = make_response(csv, response_code)
        resp.mimetype = "text/csv"
        resp.headers.add("Content-Disposition", "attachment; filename=ti.csv")
    else:
        resp = make_response(json.dumps(items, sort_keys=True, indent=4), response_code)
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
@app.route('/provider/<provider_name>/memberitems', methods=['GET', 'POST'])
def provider_memberitems(provider_name):
    logger.debug("In provider_memberitems")

    if request.method == "POST":
        logger.debug("In provider_memberitems with post")

        logger.debug("request files include" + str(request.headers))

        file = request.files['file']
        logger.debug("In provider_memberitems got file")
        logger.debug("filename = " + file.filename)
        query = file.read().decode("utf-8")
    else:
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
@app.route('/collection/<cid>', methods = ['GET'])
def collection(cid=''):
    response_code = None

    coll = mydao.get(cid)

    if request.method == "POST":
        if coll:
            # Collection already exists: should call PUT instead
            abort(405)   # Method Not Allowed
        else:
            try:
                coll = CollectionFactory.make()
                coll["item_tiids"] = request.json["items"]
                coll["title"] = request.json["title"]
                mydao.save(coll)
                response_code = 201 # Created
                logger.info("saved new collection '{id}' with {num_items} items.".format(
                    id=coll["_id"],
                    num_items=len(request.json["items"])
                ))
            except (AttributeError, TypeError):
                # we got missing or improperly formated data.
                # should log the error...
                abort(404)  #what is the right error message for 'needs arguments'?

    elif request.method == "GET":
        if coll:
            response_code = 200 #OK
        else:
            abort(404)

    resp = make_response( json.dumps( coll, sort_keys=True, indent=4 ), response_code)
    resp.mimetype = "application/json"

    return resp


@app.route('/test/collection/<action_type>', methods = ['GET'])
def tests_interactions(action_type=''):
    logger.info("getting test/collection/"+action_type)

    report = redis.hgetall("test.collection." + action_type)
    report["url"] = "http://{root}/collection/{collection_id}".format(
        root=os.getenv("WEBAPP_ROOT"),
        collection_id=report["result"]
    )

    return render_template(
        'interaction_test_report.html',
        report=report
        )


    
    