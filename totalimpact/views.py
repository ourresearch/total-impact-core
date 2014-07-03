from flask import json, request, abort, make_response, g
from flask import render_template
import sys, os
import datetime, re, copy
from werkzeug.security import check_password_hash
from collections import defaultdict
import redis
import analytics
import requests

from totalimpact import app, tiredis, collection, incoming_email, db
from totalimpact import item as item_module
from totalimpact.models import MemberItems, NotAuthenticatedError
from totalimpact.providers import provider as provider_module
from totalimpact.providers.provider import ProviderFactory, ProviderItemNotFoundError, ProviderError, ProviderServerError, ProviderTimeout
from totalimpact import unicode_helpers
from totalimpact import default_settings
from totalimpact import REDIS_MAIN_DATABASE_NUMBER
import logging


logger = logging.getLogger("ti.views")
logger.setLevel(logging.DEBUG)

mydao = None
myredis = tiredis.from_url(os.getenv("REDIS_URL"), db=REDIS_MAIN_DATABASE_NUMBER)  # main app is on DB 0

# logger.debug(u"Building reference sets")
myrefsets = None
myrefsets_histograms = None
# try:
#     (myrefsets, myrefsets_histograms) = collection.build_all_reference_lookups(myredis, mydao)
#     logger.debug(u"Reference sets dict has %i keys" %len(myrefsets.keys()))
# except (LookupError, AttributeError), e:
#     logger.error(u"Exception %s: Unable to load reference sets" % (e.__repr__()))

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


def is_valid_key(key):
    internal_keys = ["yourkey", "samplekey", "item-report-page", "api-docs", os.getenv("API_KEY").lower(), os.getenv("API_ADMIN_KEY").lower()]
    is_valid_internal_key = key.lower() in internal_keys
    return is_valid_internal_key

def check_key():
    if "/v1/" in request.url:
        api_key = request.values.get('key', '')
        if not api_key:
            api_key = request.args.get("api_admin_key", "")
        if not is_valid_key(api_key):
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



@app.before_request
def before_request():
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

    # logger.info(u"rendering output as json")
    resp.mimetype = "application/json"
    return resp


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
    abort_custom(410, "no longer supported")


@app.route('/v1/item/<tiid>', methods=['GET'])
def get_item_from_tiid(tiid, format=None, include_history=False, callback_name=None):
    try:
        item = item_module.get_item(tiid, myrefsets, myredis)
    except (LookupError, AttributeError):
        abort_custom(404, "item does not exist")

    if not item:
        abort_custom(404, "item does not exist")

    item["refresh_status"] = item_module.refresh_status(tiid, myredis)["short"]
    if not item["refresh_status"].startswith("SUCCESS"):
        response_code = 210 # not complete yet
    else:
        response_code = 200

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
    abort_custom(410, "no longer supported")



@app.route('/v1/provider', methods=['GET'])
def provider():
    ret = ProviderFactory.get_all_metadata()
    resp = make_response(json.dumps(ret, sort_keys=True, indent=4), 200)

    return resp



def format_into_products_dict(tiids_aliases_map):
    products_dict = {}
    for tiid in tiids_aliases_map:
        (ns, nid) = tiids_aliases_map[tiid]
        products_dict[tiid] = {"aliases": {ns: [nid]}}
    return products_dict



@app.route("/v1/importer/<provider_name>", methods=['POST'])
def importer_post(provider_name):
    # need to do these ugly deletes because import products not in dict.  fix in future!
    try:
        profile_id = request.json["profile_id"]
        del request.json["profile_id"]
    except KeyError:
        abort(405, "missing profile_id")

    try:
        analytics_credentials = request.json["analytics_credentials"]
        del request.json["analytics_credentials"]
    except KeyError:
        analytics_credentials = {}

    try:
        existing_tiids = request.json["existing_tiids"]
        del request.json["existing_tiids"]
    except KeyError:
        existing_tiids = []

    try:
        retrieved_aliases = provider_module.import_products(provider_name, request.json)
    except ImportError:
        abort_custom(404, "an importer for provider '{provider_name}' is not found".format(
            provider_name=provider_name))        
    except ProviderItemNotFoundError:
        abort_custom(404, "item not found")
    except ProviderItemNotFoundError:
        abort_custom(404, "item not found")
    except (ProviderTimeout, ProviderServerError):
        abort_custom(503, "timeout error, might be transient")
    except ProviderError:
        abort(500, "internal error from provider")

    new_aliases = item_module.aliases_not_in_existing_tiids(retrieved_aliases, existing_tiids)
    tiids_aliases_map = item_module.create_tiids_from_aliases(profile_id, new_aliases, analytics_credentials, myredis, provider_name)
    # logger.debug(u"in provider_importer_get with {tiids_aliases_map}".format(
    #     tiids_aliases_map=tiids_aliases_map))

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
    # logger.info(u"in collection_get".format(cid=cid))

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
                analytics_credentials={},
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



def refresh_from_tiids(tiids, analytics_credentials, priority, myredis):
    item_objects = item_module.Item.query.filter(item_module.Item.tiid.in_(tiids)).all()
    dicts_to_refresh = []  

    for item_obj in item_objects:
        try:
            tiid = item_obj.tiid
            item_obj.set_last_refresh_start()
            db.session.add(item_obj)
            alias_dict = item_module.alias_dict_from_tuples(item_obj.alias_tuples)       
            dicts_to_refresh += [{"tiid":tiid, "aliases_dict": alias_dict}]
        except AttributeError:
            logger.debug(u"couldn't find tiid {tiid} so not refreshing its metrics".format(
                tiid=tiid))

    db.session.commit()

    item_module.start_item_update(dicts_to_refresh, priority, myredis)
    return tiids


""" Refreshes all the items from tiids
    Depricate this one
"""
@app.route("/v1/products/<tiids_string>", methods=["POST"])
# not officially supported in api
def products_refresh_post_inline(tiids_string):
    tiids = tiids_string.split(",")
    try:
        analytics_credentials = request.json["analytics_credentials"]
    except KeyError:
        analytics_credentials = {}

    try:
        priority = request.json["priority"]
    except KeyError:
        priority = "high"

    refresh_from_tiids(tiids, analytics_credentials, priority, myredis)
    resp = make_response("true", 200)
    return resp


# refreshes items from tiids list in body of POST
@app.route('/v1/products/refresh', methods=['POST'])
def products_refresh_post():
    # logger.debug(u"in products_refresh_post with tiids")
    tiids = request.json["tiids"]
    try:
        analytics_credentials = request.json["analytics_credentials"]
    except KeyError:
        analytics_credentials = {}

    try:
        priority = request.json["priority"]
    except KeyError:
        priority = "high"

    refresh_from_tiids(tiids, analytics_credentials, priority, myredis)
    resp = make_response("true", 200)    
    return resp


# sends back duplicate groups from tiids list in body of POST
@app.route('/v1/products/duplicates', methods=['POST'])
def products_duplicates_post():
    # logger.debug(u"in products_duplicates_post with tiids")
    tiids = request.json["tiids"]
    duplicates_list = item_module.build_duplicates_list(tiids)
    resp = make_response(json.dumps({"duplicates_list": duplicates_list}, sort_keys=True, indent=4), 200)   
    return resp


""" Refreshes all the items in a given collection.
    Still useful for refsets!
"""
@app.route("/v1/collection/<cid>", methods=["POST"])
# not officially supported in api, though still useful for refsets
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

    refresh_from_tiids(tiids, {}, "low", myredis)

    resp = make_response("true", 200)
    return resp



@app.route("/v1/collection/<cid>", methods=["DELETE"])
def delete_collection(cid=None):
    abort_custom(501, "Deleting collections is not currently supported.")



# creates products from aliases or returns items from tiids
@app.route('/v1/products', methods=['POST'])
@app.route('/v1/products.<format>', methods=['POST'])
def products_post(format="json"):
    if "tiids" in request.json:
        # overloading post for get because tiids string gets long
        # logger.debug(u"in products_post with tiids, so getting products to return")
        tiids = request.json["tiids"]
        tiids_string = ",".join(tiids)
        try:
            most_recent_metric_date = request.json["most_recent_metric_date"]
            most_recent_diff_metric_date = request.json["most_recent_diff_metric_date"]
        except KeyError:
            most_recent_metric_date = None
            most_recent_diff_metric_date = None

        return products_get(tiids_string, format, most_recent_metric_date, most_recent_diff_metric_date)
    else:
        abort_custom(400, "bad arguments")


def cleaned_items(tiids, myredis, override_export_clean=False, most_recent_metric_date=None, most_recent_diff_metric_date=None):
    items_dict = collection.get_items_for_client(tiids, myrefsets, myredis, most_recent_metric_date, most_recent_diff_metric_date)

    secret_key = os.getenv("API_ADMIN_KEY")
    supplied_key = request.args.get("api_admin_key", "")
    cleaned_items_dict = {}
    for tiid in items_dict:
        cleaned_items_dict[tiid] = item_module.clean_for_export(items_dict[tiid], supplied_key, secret_key, override_export_clean)
    return cleaned_items_dict


# returns a product from a tiid
@app.route('/v1/product/<tiid>', methods=['GET'])
def single_product_get(tiid):
    cleaned_items_dict = cleaned_items([tiid], myredis)
    try:
        single_item = cleaned_items_dict[tiid]
    except TypeError:
        abort_custom(404, "No product found with that tiid")

    response_code = 200
    if not collection.is_all_done([tiid], myredis):
        response_code = 210 # update is not complete yet

    resp = make_response(json.dumps(single_item, sort_keys=True, indent=4),
                         response_code)

    return resp


# returns products from tiids
@app.route('/v1/products/<tiids_string>', methods=['GET'])
@app.route('/v1/products.<format>/<tiids_string>', methods=['GET'])
def products_get(tiids_string, format="json", most_recent_metric_date=None, most_recent_diff_metric_date=None):
    tiids = tiids_string.split(",")
    override_export_clean = (format=="csv")
    cleaned_items_dict = cleaned_items(tiids, myredis, override_export_clean, most_recent_metric_date, most_recent_diff_metric_date)

    response_code = 200
    if not collection.is_all_done(tiids, myredis):
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


@app.route("/v1/product/<tiid>/biblio", methods=["PATCH"])
def product_biblio_modify(tiid):
    data = request.json
    for biblio_field_name in data:
        item = item_module.add_biblio(tiid, biblio_field_name, data[biblio_field_name])
    response = {"product": item.as_old_doc()}
    return make_response(json.dumps(response, indent=4), 200)



# for internal use only
@app.route('/test/collection/<action_type>', methods=['GET'])
def tests_interactions(action_type=''):
    # logger.info(u"getting test/collection/" + action_type)

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

@app.route("/collections/reference-sets-medians")
def reference_sets_medians():
    refset_medians = defaultdict(dict)
    for genre in myrefsets_histograms:
        if not genre in refset_medians:
            refset_medians[genre] = {}
        for refset in myrefsets_histograms[genre]:
            if not refset in refset_medians[genre]:
                refset_medians[genre][refset] = {}
            for year in myrefsets_histograms[genre][refset]:
                if not year in refset_medians[genre][refset]:
                    refset_medians[genre][refset][year] = {}
                for metric_name in myrefsets_histograms[genre][refset][year]:
                    median = myrefsets_histograms[genre][refset][year][metric_name][50]
                    refset_medians[genre][refset][year][metric_name] = median
    resp = make_response(json.dumps(refset_medians, indent=4), 200)

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


