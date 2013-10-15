from flask import json, request, abort, make_response, g
from flask import render_template
import sys, os
import datetime, re, copy
from werkzeug.security import check_password_hash
from collections import defaultdict
import redis
import shortuuid
import analytics
import requests

from totalimpact import app, tiredis, collection, api_user, incoming_email
from totalimpact import item as item_module
from totalimpact.models import MemberItems, NotAuthenticatedError
from totalimpact.providers.provider import ProviderFactory, ProviderItemNotFoundError, ProviderError, ProviderServerError, ProviderTimeout
from totalimpact import unicode_helpers
from totalimpact import default_settings
import logging


logger = logging.getLogger("ti.views")
logger.setLevel(logging.DEBUG)

mydao = None
myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"), db=0)  # main app is on DB 0

logger.debug(u"Building reference sets")
myrefsets = None
myrefsets_histograms = None
try:
    (myrefsets, myrefsets_histograms) = collection.build_all_reference_lookups(myredis, mydao)
    logger.debug(u"Reference sets dict has %i keys" %len(myrefsets.keys()))
except (LookupError, AttributeError), e:
    logger.error(u"Exception %s: Unable to load reference sets" % (e.__repr__()))

def set_db(url, db):
    """useful for unit testing, where you want to use a local database
    """
    global mydao 
    mydao = None
    return mydao

def set_redis(url, db):
    """useful for unit testing, where you want to use a local database
    """
    global myredis 
    myredis = tiredis.from_url(url, db)
    return myredis



def check_key():
    if request.values.get("api_admin_key"):
        return

    if "/v1/" in request.url:
        api_key = request.values.get('key', '')
        if not api_user.is_valid_key(api_key):
            abort_custom(403, "You must include key=YOURKEY in your query.  Contact team@impactstory.org for a valid api key.")
    return # if success don't return any content


def abort_custom(status_code, msg):
    body_dict = {
        "HTTP_status_code": status_code,
        "message": msg,
        "error": True
    }
    if request.args.get("callback"):
        status_code = 200  # JSONP can't deal with actual errors, it needs something back
        resp_string = "{callback_name}( {resp} )".format(
            callback_name=request.args.get("callback"),
            resp=json.dumps(body_dict)
        )
    else:
        resp_string = json.dumps(body_dict, sort_keys=True, indent=4)

    resp = make_response(resp_string, status_code)
    resp.mimetype = "application/json"
    abort(resp)

def check_mimetype():
    g.return_as_html = False
    if request.path.endswith(".html"):
        g.return_as_html = True
        request.path = request.path.replace(".html", "")

def stop_user_who_is_swamping_us():
    ip = request.remote_addr
    key = request.values.get('key', '')
    if ip in ["91.121.68.140"]:
        logger.debug(u"got a call from {ip}; aborting with 403.".format(ip=ip) )
        abort_custom(403, """Sorry, we're blocking your IP address {ip} because \
            we can't handle requests as quickly as you're sending them, and so
            they're swamping our system. Please email us at \
            team@impactstory.org for details and possible workarounds.
        """.format(ip=ip))

    # if key  in ["VANWIJIKc233acaa"]:
    #     logger.debug(u"got a call from {key}; aborting with 403.".format(key=key) )
    #     abort(403, """Sorry, we're blocking your api key '{key}' because \
    #             we can't handle requests as quickly as you're sending them, and so
    #             they're swamping our system. Please email us at \
    #             team@impactstory.org for details and possible workarounds.
    #         """.format(key=key))


@app.before_request
def before_request():
    stop_user_who_is_swamping_us()
    track_api_event()
    check_key()
    check_mimetype()


@app.after_request
def add_crossdomain_header(resp):
    #support CORS    
    resp.headers['Access-Control-Allow-Origin'] = "*"
    resp.headers['Access-Control-Allow-Methods'] = "POST, GET, OPTIONS, PUT, DELETE"
    resp.headers['Access-Control-Allow-Headers'] = "origin, content-type, accept, x-requested-with"
    return resp

@app.after_request
def set_mimetype_and_encoding(resp):
    resp.headers.add("Content-Encoding", "UTF-8")

    if "csv" in resp.mimetype:
        return resp
    if "static" in request.path:
        return resp

    try:
        if g.return_as_html:
            logger.info(u"rendering output through debug_api.html template")
            resp.mimetype = "text/html"
            return make_response(render_template(
                'debug_api.html',
                data=resp.data))
    except AttributeError:
        pass

    logger.info(u"rendering output as json")
    resp.mimetype = "application/json"
    return resp


def track_api_event():
    api_key = request.values.get('key')
    if not api_key:
        api_key = request.args.get("api_admin_key", "")

    if not api_user.is_internal_key(api_key):
        if request.path not in ["/favicon.ico"]:
            requested_to_create_item = False
            requested_to_view_item = False
            if ("/v1/item" in request.url):
                if (request.method == "POST"):
                    requested_to_create_item = True
                elif (request.method == "GET"):
                    requested_to_view_item = True
                    if (request.args.get("register", 0) in ["1", "true", "True"]):
                        requested_to_create_item = True

            analytics.track("CORE", "Received API request from external", {
                "path": request.path, 
                "url": request.url, 
                "method": request.method, 
                "requested_to_create_item": requested_to_create_item, 
                "requested_to_view_item": requested_to_view_item, 
                "user_agent": request.user_agent.string,
                "api_key": api_key
                }, 
                context={ "providers": { 'Mixpanel': False } })

# adding a simple route to confirm working API
@app.route('/')
@app.route('/v1')
def hello():
    msg = {
        "hello": "world",
        "message": "Congratulations! You have found the ImpactStory API.",
        "more-info": "http://impactstory.org/api-docs",
        "contact": "team@impactstory.org",
        "version": app.config["VERSION"]
    }
    resp = make_response(json.dumps(msg, sort_keys=True, indent=4), 200)
    return resp


@app.route('/v1/item/<namespace>/<path:nid>', methods=['POST'])
def item_namespace_post(namespace, nid):
    namespace = item_module.clean_id(namespace)
    nid = item_module.clean_id(nid)

    api_key = request.values.get('key')
    try:
        api_user.register_item((namespace, nid), api_key, myredis, mydao)
        response_code = 201 # Created
    except api_user.ItemAlreadyRegisteredToThisKey:
        response_code = 200
    except api_user.ApiLimitExceededException:
        abort_custom(403, "Registration limit exceeded. Contact team@impactstory.org to discuss options.")

    resp = make_response(json.dumps("ok"), response_code)
    return resp


@app.route('/v1/item/<tiid>', methods=['GET'])
def get_item_from_tiid(tiid, format=None, include_history=False, callback_name=None):
    try:
        item = item_module.get_item(tiid, myrefsets, mydao, include_history)
    except (LookupError, AttributeError):
        abort_custom(404, "item does not exist")

    if not item:
        abort_custom(404, "item does not exist")

    if item_module.is_currently_updating(tiid, myredis):
        response_code = 210 # not complete yet
        item["currently_updating"] = True
    else:
        response_code = 200
        item["currently_updating"] = False

    api_key = request.args.get("key", None)
    clean_item = item_module.clean_for_export(item, api_key, os.getenv("API_ADMIN_KEY"))
    clean_item["HTTP_status_code"] = response_code  # hack for clients who can't read real response codes

    resp_string = json.dumps(clean_item, sort_keys=True, indent=4)
    if callback_name is not None:
        resp_string = callback_name + '(' + resp_string + ')'

    resp = make_response(resp_string, response_code)

    return resp

@app.route('/v1/tiid/<namespace>/<path:nid>', methods=['GET'])
def get_tiid_from_namespace_nid(namespace, nid):
    tiid = item_module.get_tiid_by_alias(namespace, nid)
    if not tiid:
        abort_custom(404, "alias not in database")
    return make_response(json.dumps({"tiid": tiid}, sort_keys=True, indent=4), 200)


@app.route('/v1/item/<namespace>/<path:nid>', methods=['GET'])
def get_item_from_namespace_nid(namespace, nid, format=None, include_history=False):
    namespace = item_module.clean_id(namespace)
    nid = item_module.clean_id(nid)

    include_history = request.args.get("include_history", 0) in ["1", "true", "True"]
    register = request.args.get("register", 0) in ["1", "true", "True"]
    callback_name = request.args.get("callback", None)
    api_key = request.values.get('key')

    debug_message = ""
    if register:
        try:
            api_user.register_item((namespace, nid), api_key, myredis, mydao)
        except api_user.ItemAlreadyRegisteredToThisKey:
            debug_message = u"ItemAlreadyRegisteredToThisKey for key {api_key}".format(
                api_key=api_key)
            logger.debug(debug_message)
        except api_user.ApiLimitExceededException:
            debug_message = u"ApiLimitExceededException for key {api_key}".format(
                api_key=api_key)
            logger.debug(debug_message)

    tiid = item_module.get_tiid_by_alias(namespace, nid, mydao)
    if not tiid:
        if not debug_message:
            debug_message = "Item not in database. Call POST to register it"
        # if registration failure, report that info. Else suggest they register.
        abort_custom(404, debug_message)
    return get_item_from_tiid(tiid, format, include_history, callback_name)



@app.route('/v1/provider', methods=['GET'])
def provider():
    ret = ProviderFactory.get_all_metadata()
    resp = make_response(json.dumps(ret, sort_keys=True, indent=4), 200)

    return resp

@app.route('/v1/provider/<provider_name>/memberitems', methods=['POST'])
def provider_memberitems(provider_name):
    """
    Make a descr string (like bibtex) into a dict strings describing items.
    """

    provider = ProviderFactory.get_provider(provider_name)
    items_dict = provider.parse(request.json["descr"])

    resp = make_response(
        json.dumps({"memberitems": items_dict}, sort_keys=True, indent=4),
        200
    )
    return resp

@app.route("/v1/provider/<provider_name>/memberitems/<query>", methods=['GET'])
def provider_memberitems_get(provider_name, query):
    """
    Gets aliases associated with a query from a given provider.
    """
    query = unicode_helpers.remove_nonprinting_characters(query)
    provider = ProviderFactory.get_provider(provider_name)

    try:
        items_dict = provider.member_items(query)

    except ProviderItemNotFoundError:
        abort_custom(404, "item not found")

    except (ProviderTimeout, ProviderServerError):
        abort_custom(503, "crossref lookup error, might be transient")

    except ProviderError:
        abort(500, "internal error from provider")

    resp = make_response(
        json.dumps({"memberitems": items_dict}, sort_keys=True, indent=4),
        200
    )
    return resp


def format_into_products_dict(tiids_aliases_map):
    products_dict = {}
    for tiid in tiids_aliases_map:
        (ns, nid) = tiids_aliases_map[tiid]
        products_dict[tiid] = {"aliases": {ns: [nid]}}
    return products_dict


@app.route("/v1/importer/<provider_name>", methods=['POST'])
def importer_post(provider_name):
    """
    Gets aliases associated with a query from a given provider.
    """
    input_string = request.json["input"]

    if provider_name == "pmids":
        provider_name = "pubmed"
    elif provider_name == "dois":
        provider_name = "crossref"
    elif provider_name == "urls":
        provider_name = "webpage"
    try:
        provider = ProviderFactory.get_provider(provider_name)
    except ImportError:
        abort_custom(404, "an importer for provider '{provider_name}' is not found".format(
            provider_name=provider_name))

    try:
        aliases = provider.member_items(input_string)
    except ProviderItemNotFoundError:
        abort_custom(404, "item not found")
    except (ProviderTimeout, ProviderServerError):
        abort_custom(503, "timeout error, might be transient")
    except ProviderError:
        abort(500, "internal error from provider")

    tiids_aliases_map = item_module.create_tiids_from_aliases(aliases, myredis)
    logger.debug(u"in provider_importer_get with {tiids_aliases_map}".format(
        tiids_aliases_map=tiids_aliases_map))

    products_dict = format_into_products_dict(tiids_aliases_map)

    resp = make_response(json.dumps({"products": products_dict}, sort_keys=True, indent=4), 200)
    return resp


def abort_if_fails_collection_edit_auth(request):
    if request.args.get("api_admin_key"):
        supplied_key = request.args.get("api_admin_key", "")
        if os.getenv("API_KEY") == supplied_key:  #remove this once webapp sends admin_api_key
            return True
        if os.getenv("API_ADMIN_KEY") == supplied_key:
            return True
    abort_custom(403, "This collection has no update key; it can't be changed.")


def get_alias_strings(aliases):
    alias_strings = []
    for (namespace, nid) in aliases:
        namespace = item_module.clean_id(namespace)
        nid = item_module.clean_id(nid)
        try:
            alias_strings += [namespace+":"+nid]
        except TypeError:
            # jsonify the biblio dicts
            alias_strings += [namespace+":"+json.dumps(nid)]
    return alias_strings   



'''
GET /collection/:collection_ID
returns a collection object and the items
'''
@app.route('/v1/collection/<cid>', methods=['GET'])
@app.route('/v1/collection/<cid>.<format>', methods=['GET'])
def collection_get(cid='', format="json", include_history=False):
    logger.info(u"in collection_get".format(cid=cid))

    # if not include items, then just return the collection straight from couch
    if (request.args.get("include_items") in ["0", "false", "False"]):
        coll = collection.get_collection_doc(cid)
        if not coll:
            abort_custom(404, "collection not found")

        # except if format is csv.  can't do that.
        if format == "csv":
            abort_custom(405, "csv method not supported for not include_items")
        else:
            response_code = 200
            resp = make_response(json.dumps(coll, sort_keys=True, indent=4),
                                 response_code)
    else:
        include_history = (request.args.get("include_history", 0) in ["1", "true", "True"])
        (coll_with_items, something_currently_updating) = collection.get_collection_with_items_for_client(cid, myrefsets, myredis, mydao, include_history)

        # return success if all reporting is complete for all items    
        if something_currently_updating:
            response_code = 210 # update is not complete yet
        else:
            response_code = 200

        if format == "csv":
            # remove scopus before exporting to csv, so don't add magic keep-scopus keys to clean method
            clean_items = [item_module.clean_for_export(item) for item in coll_with_items["items"]]
            csv = collection.make_csv_stream(clean_items)
            resp = make_response(csv, response_code)
            resp.mimetype = "text/csv;charset=UTF-8"
            resp.headers.add("Content-Disposition",
                             "attachment; filename=impactstory-{cid}.csv".format(
                                cid=cid))
            resp.headers.add("Content-Encoding",
                             "UTF-8")
        else:

            secret_key = os.getenv("API_ADMIN_KEY") 
            if request.args.get("api_admin_key"):
                supplied_key = request.args.get("api_admin_key", "")
            else:
                supplied_key = request.args.get("key", "")

            clean_if_necessary_items = [item_module.clean_for_export(item, supplied_key, secret_key)
                for item in coll_with_items["items"]]

            coll_with_items["items"] = clean_if_necessary_items
            resp = make_response(json.dumps(coll_with_items, sort_keys=True, indent=4),
                                 response_code)
    return resp


@app.route('/v1/collection/<cid>/items', methods=['POST'])
def delete_and_put_helper(cid=""):
    """
    Lets browsers who can't do PUT or DELETE fake it with a POST
    """
    http_method = request.args.get("http_method", "")
    if http_method.lower() == "delete":
        return remove_items_from_collection(cid)
    elif http_method.lower() == "put":
        return add_items_to_collection(cid)
    else:
        abort_custom(404, "You must specify a valid HTTP method (POST or PUT) with the"
                   " http_method argument.")


@app.route('/v1/collection/<cid>/items', methods=['DELETE'])
def remove_items_from_collection(cid=""):
    """
    Deletes items from a collection
    """
    abort_if_fails_collection_edit_auth(request)

    try:
        collection_object = collection.remove_items_from_collection(
            cid=cid, 
            tiids_to_delete=request.json["tiids"], 
            myredis=myredis, 
            mydao=mydao)
    except (AttributeError, TypeError, KeyError) as e:
        # we got missing or improperly formated data.
        logger.error(u"DELETE /collection/{id}/items threw an error: '{error_str}'. input: {json}.".format(
                id=cid,
                error_str=e,
                json=request.json))
        abort_custom(500, "Error deleting items from collection")

    (coll_doc, is_updating) = collection.get_collection_with_items_for_client(cid, myrefsets, myredis, mydao, include_history=False)
    resp = make_response(json.dumps(coll_doc, sort_keys=True, indent=4), 200)
    return resp


@app.route("/v1/collection/<cid>/items", methods=["PUT"])
def add_items_to_collection(cid=""):
    """
    Adds new items to a collection.
    """

    abort_if_fails_collection_edit_auth(request)

    try:
        if "tiids" in request.json:
            collection_object = collection.add_items_to_collection_object(
                    cid=cid, 
                    tiids=request.json["tiids"], 
                    alias_tuples=None)
        else:
            #to be depricated
            collection_object = collection.add_items_to_collection(
                cid=cid, 
                aliases=request.json["aliases"], 
                myredis=myredis)
    except (AttributeError, TypeError) as e:
        # we got missing or improperly formated data.
        logger.error(u"PUT /collection/{id}/items threw an error: '{error_str}'. input: {json}.".format(
                id=cid,
                error_str=e,
                json=request.json))
        abort_custom(500, "Error adding items to collection")

    (coll_doc, is_updating) = collection.get_collection_with_items_for_client(cid, myrefsets, myredis, mydao, include_history=False)

    resp = make_response(json.dumps(coll_doc, sort_keys=True, indent=4), 200)

    return resp



""" Refreshes all the items from tiids
"""
@app.route("/v1/products/<tiids_string>", methods=["POST"])
# not officially supported in api
def products_refresh_post(tiids_string):
    tiids = tiids_string.split(",")
    for tiid in tiids:
        try:
            item_obj = item_module.Item.from_tiid(tiid)
            item = item_obj.as_old_doc()        
            item_module.start_item_update(tiid, item["aliases"], myredis)
        except AttributeError:
            logger.debug(u"couldn't find tiid {tiid} in {cid} so not refreshing its metrics".format(
                cid=cid, tiid=tiid))

    resp = make_response("true", 200)
    return resp



""" Refreshes all the items in a given collection.
"""
@app.route("/v1/collection/<cid>", methods=["POST"])
# not officially supported in api
def collection_metrics_refresh(cid=""):

    # first, get the tiids in this collection:
    try:
        coll_doc = collection.get_collection_doc(cid)
        tiids = coll_doc["alias_tiids"].values()
    except (TypeError, AttributeError):
        logger.exception(u"couldn't get tiids in POST collection '{cid}'".format(
            cid=cid
        ))
        abort_custom(500, "Error doing collection_update")

    for tiid in tiids:
        try:
            item_obj = item_module.Item.from_tiid(tiid)
            item = item_obj.as_old_doc()        
            item_module.start_item_update(tiid, item["aliases"], myredis)
        except AttributeError:
            logger.debug(u"couldn't find tiid {tiid} in {cid} so not refreshing its metrics".format(
                cid=cid, tiid=tiid))

    resp = make_response("true", 200)
    return resp


@app.route("/v1/collection/<cid>", methods=["DELETE"])
def delete_collection(cid=None):
    abort_custom(501, "Deleting collections is not currently supported.")



# creates products from aliases
@app.route('/v1/products', methods=['POST'])
def products_create():
    tiids_aliases_map = item_module.create_tiids_from_aliases(request.json["aliases"], myredis)
    products_dict = format_into_products_dict(tiids_aliases_map)

    resp = make_response(json.dumps({"products": products_dict}, sort_keys=True, indent=4), 200)

    return resp


def cleaned_items(tiids):
    items_dict = collection.get_items_for_client(tiids, myrefsets)

    secret_key = os.getenv("API_ADMIN_KEY")
    supplied_key = request.args.get("api_admin_key", "")
    cleaned_items_dict = {}
    for tiid in items_dict:
        cleaned_items_dict[tiid] = item_module.clean_for_export(items_dict[tiid], supplied_key, secret_key)
    return cleaned_items_dict


# returns a product from a tiid
@app.route('/v1/product/<tiid>', methods=['GET'])
def single_product_get(tiid):
    cleaned_items_dict = cleaned_items([tiid])
    try:
        single_item = cleaned_items_dict[tiid]
    except TypeError:
        abort_custom(404, "No product found with that tiid")

    response_code = 200
    if collection.is_something_currently_updating(cleaned_items_dict, myredis):
        response_code = 210 # update is not complete yet

    resp = make_response(json.dumps(single_item, sort_keys=True, indent=4),
                         response_code)

    return resp


# returns products from tiids
@app.route('/v1/products/<tiids_string>', methods=['GET'])
@app.route('/v1/products.<format>/<tiids_string>', methods=['GET'])
def products_get(tiids_string, format="json"):
    tiids = tiids_string.split(",")
    cleaned_items_dict = cleaned_items(tiids)

    response_code = 200
    if collection.is_something_currently_updating(cleaned_items_dict, myredis):
        response_code = 210 # update is not complete yet

    if format == "csv":
        csv = collection.make_csv_stream(cleaned_items_dict.values())
        resp = make_response(csv, response_code)
        resp.mimetype = "text/csv;charset=UTF-8"
        resp.headers.add("Content-Encoding", "UTF-8")
    else:
        resp = make_response(json.dumps({"products": cleaned_items_dict}, sort_keys=True, indent=4),
                             response_code)

    return resp




# creates a collection from aliases or tiids
@app.route('/v1/collection', methods=['POST'])
def collection_create():
    """
    POST /collection
    creates new collection
    """
    response_code = None
    try:
        cid = request.args.get("collection_id", collection._make_id())
        if "tiids" in request.json:
            (coll_doc, collection_object) = collection.create_new_collection_from_tiids(
                cid=cid, 
                title=request.json.get("title", "my collection"), 
                tiids=request.json.get("tiids"), 
                ip_address=request.remote_addr, 
                refset_metadata=request.json.get("refset_metadata", None))
        else:
            # to be depricated
            (coll_doc, collection_object) = collection.create_new_collection(
                cid=cid, 
                title=request.json.get("title", "my collection"), 
                aliases=request.json["aliases"], 
                ip_address=request.remote_addr, 
                refset_metadata=request.json.get("refset_metadata", None), 
                myredis=myredis, 
                mydao=mydao)
    except (AttributeError, TypeError):
        # we got missing or improperly formated data.
        logger.error(u"we got missing or improperly formated data: '{cid}' with {json}.".format(
                cid=cid,
                json=str(request.json)))
        abort_custom(404, "Missing arguments.")

    response_code = 201 # Created
    resp = make_response(json.dumps({"collection":coll_doc},
            sort_keys=True, indent=4), response_code)
    return resp





# for internal use only
@app.route('/test/collection/<action_type>', methods=['GET'])
def tests_interactions(action_type=''):
    logger.info(u"getting test/collection/" + action_type)

    report = myredis.hgetall("test.collection." + action_type)
    report["url"] = "http://{root}/collection/{collection_id}".format(
        root=os.getenv("WEBAPP_ROOT"),
        collection_id=report["result"]
    )

    return render_template(
        'interaction_test_report.html',
        report=report
    )
       


@app.route("/v1/collections/<cids>")
def get_collection_titles(cids=''):
    from time import sleep
    sleep(1)
    cids_arr = cids.split(",")
    coll_info = collection.get_titles(cids_arr, mydao)
    resp = make_response(json.dumps(coll_info, indent=4), 200)
    return resp


@app.route("/v1/collections/reference-sets")
def reference_sets():
    resp = make_response(json.dumps(myrefsets, indent=4), 200)
    return resp

@app.route("/v1/collections/reference-sets-histograms")
def reference_sets_histograms():
    rows = []
    header_added = False
    for genre in myrefsets_histograms:
        for refset in myrefsets_histograms[genre]:
            for year in myrefsets_histograms[genre][refset]:
                if not header_added:
                    first_metric_name = myrefsets_histograms[genre][refset][year].keys()[0]
                    data_labels = [str(i)+"th" for i in range(len(myrefsets_histograms[genre][refset][year][first_metric_name]))]
                    header = ",".join(["genre", "refset", "year", "metric_name"] + data_labels)
                    rows.append(header)
                    header_added = True
                for metric_name in myrefsets_histograms[genre][refset][year]:
                    metadata = [genre, refset, str(year), metric_name]
                    metrics = [str(i) for i in myrefsets_histograms[genre][refset][year][metric_name]]
                    rows.append(",".join(metadata+metrics))
    resp = make_response("\n".join(rows), 200)
    # Do we want it to pop up to save?  kinda nice to just see it in browser
    #resp.mimetype = "text/csv;charset=UTF-8"
    #resp.headers.add("Content-Disposition", "attachment; filename=refsets.csv")
    #resp.headers.add("Content-Encoding", "UTF-8")
    return resp

@app.route("/v1/key", methods=["POST"])
def key():
    """ Generate a new api key and store api key info in a db doc """
    meta = request.json
    if meta["password"] != os.getenv("API_KEY"):
        abort_custom(403, "password not correct")
    del meta["password"]

    new_api_user = api_user.save_api_user(**meta)
    new_api_key = new_api_user.api_key

    resp = make_response(json.dumps({"api_key":new_api_key}, indent=4), 200)
    return resp



# route to receive email
@app.route('/v1/inbox', methods=["POST"])
def inbox():
    payload = request.json
    email = incoming_email.save_incoming_email(payload)
    logger.info(u"You've got mail. Subject: {subject}".format(
        subject=email.subject))
    resp = make_response(json.dumps({"subject":email.subject}, sort_keys=True, indent=4), 200)
    return resp


