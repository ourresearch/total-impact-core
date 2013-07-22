from flask import json, request, abort, make_response
from flask import render_template
import sys, os
import datetime, re, couchdb, copy
from werkzeug.security import check_password_hash
from collections import defaultdict
import redis
import shortuuid
import analytics

from totalimpact import dao, app, tiredis, collection, api_user
from totalimpact import item as item_module
from totalimpact.models import MemberItems, UserFactory, NotAuthenticatedError
from totalimpact.providers.provider import ProviderFactory, ProviderItemNotFoundError, ProviderError, ProviderServerError, ProviderTimeout
from totalimpact import default_settings
import logging


logger = logging.getLogger("ti.views")
logger.setLevel(logging.DEBUG)

mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.getenv("CLOUDANT_DB"))
mypostgresdao = dao.PostgresDao(os.environ["POSTGRESQL_URL"])
myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"), db=0)  # main app is on DB 0

logger.debug("Building reference sets")
myrefsets = None
myrefsets_histograms = None
try:
    (myrefsets, myrefsets_histograms) = collection.build_all_reference_lookups(myredis, mydao)
    logger.debug("Reference sets dict has %i keys" %len(myrefsets.keys()))
except (couchdb.ResourceNotFound, LookupError, AttributeError), e:
    logger.error("Exception %s: Unable to load reference sets" % (e.__repr__()))

def set_db(url, db):
    """useful for unit testing, where you want to use a local database
    """
    global mydao 
    mydao = dao.Dao(url, db)
    return mydao

def set_redis(url, db):
    """useful for unit testing, where you want to use a local database
    """
    global myredis 
    myredis = tiredis.from_url(url, db)
    return myredis

@app.before_request
def stop_user_who_is_swamping_us():
    ip = request.remote_addr
    key = request.values.get('key', '')
    if ip in ["91.121.68.140"]:
        logger.debug("got a call from {ip}; aborting with 403.".format(ip=ip) )
        abort(403, """Sorry, we're blocking your IP address {ip} because \
            we can't handle requests as quickly as you're sending them, and so
            they're swamping our system. Please email us at \
            team@impactstory.org for details and possible workarounds.
        """.format(ip=ip))

    # if key  in ["VANWIJIKc233acaa"]:
    #     logger.debug("got a call from {key}; aborting with 403.".format(key=key) )
    #     abort(403, """Sorry, we're blocking your api key '{key}' because \
    #             we can't handle requests as quickly as you're sending them, and so
    #             they're swamping our system. Please email us at \
    #             team@impactstory.org for details and possible workarounds.
    #         """.format(key=key))


def check_key():
    if request.args.get("api_admin_key"):
        return

    if "/v1/" in request.url:
        api_key = request.values.get('key', '')
        if not api_user.is_valid_key(api_key, mypostgresdao):
            abort(403, "You must include key=YOURKEY in your query.  Contact team@impactstory.org for a valid api key.")
    return # if success don't return any content


def track_api_event():
    api_key = request.values.get('key')
    if not api_key:
        api_key = request.args.get("api_admin_key", "")

    if api_user.is_internal_key(api_key):
        analytics.track("CORE", "Received API request from webapp", {
            "path": request.path, 
            "method": request.method 
            })
    else:
        analytics.track("CORE", "Received API request from external", {
            "path": request.path, 
            "method": request.method, 
            "user_agent": request.user_agent.string,
            "api_key": api_key
            })


@app.before_request
def before_request():
    track_api_event()
    check_key()


@app.after_request
def add_crossdomain_header(resp):
    #support CORS    
    resp.headers['Access-Control-Allow-Origin'] = "*"
    resp.headers['Access-Control-Allow-Methods'] = "POST, GET, OPTIONS, PUT, DELETE"
    resp.headers['Access-Control-Allow-Headers'] = "origin, content-type, accept, x-requested-with"
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
    resp.mimetype = "application/json"
    return resp


'''
GET /tiid/:namespace/:id
404 if not found because not created yet
303 else list of tiids
'''
@app.route('/tiid/<ns>/<path:nid>', methods=['GET'])
# not supported in v1
def tiid(ns, nid):
    ns = item_module.clean_id(ns)
    nid = item_module.clean_id(nid)

    tiid = item_module.get_tiid_by_alias(ns, nid, mydao)

    if not tiid:
        abort(404)
    resp = make_response(json.dumps(tiid, sort_keys=True, indent=4), 303)
    resp.mimetype = "application/json"
    return resp


@app.route('/item/<namespace>/<path:nid>', methods=['POST'])
def item_namespace_post_with_tiid(namespace, nid):
    """Creates a new item using the given namespace and id.
    POST /item/:namespace/:nid
    201
    500?  if fails to create
    example /item/PMID/234234232
    original api returned tiid
    /v1 returns nothing in body
    """
    namespace = item_module.clean_id(namespace)
    nid = item_module.clean_id(nid)

    tiid = item_module.create_item_from_namespace_nid(namespace, nid, myredis, mydao)
    response_code = 201 # Created
    resp = make_response(json.dumps(tiid), response_code)
    resp.mimetype = "application/json"
    return resp

@app.route('/v1/item/<namespace>/<path:nid>', methods=['POST'])
def item_namespace_post(namespace, nid):
    namespace = item_module.clean_id(namespace)
    nid = item_module.clean_id(nid)

    api_key = request.values.get('key')
    try:
        api_user.register_item((namespace, nid), api_key, myredis, mydao, mypostgresdao)
        response_code = 201 # Created
    except api_user.ItemAlreadyRegisteredToThisKey:
        response_code = 200
    except api_user.ApiLimitExceededException:
        abort(403, "Registration limit exceeded. Contact team@impactstory.org to discuss options.")

    resp = make_response(json.dumps("ok"), response_code)
    return resp

# For /v1 support interface as get from namespace:nid instead of get from tiid
@app.route('/v1/item/<namespace>/<path:nid>', methods=['GET'])
def get_item_from_namespace_nid(namespace, nid, format=None, include_history=False):
    namespace = item_module.clean_id(namespace)
    nid = item_module.clean_id(nid)

    include_history = request.args.get("include_history", 0) in ["1", "true", "True"]
    register = request.args.get("register", 0) in ["1", "true", "True"]
    api_key = request.values.get('key')

    debug_message = ""
    if register:
        try:
            logger.debug("api_key is " + api_key)
            api_user.register_item((namespace, nid), api_key, myredis, mydao, mypostgresdao)
        except api_user.ItemAlreadyRegisteredToThisKey:
            debug_message = "ItemAlreadyRegisteredToThisKey for key {api_key}".format(
                api_key=api_key)
            logger.debug(debug_message)
        except api_user.ApiLimitExceededException:
            debug_message = "ApiLimitExceededException for key {api_key}".format(
                api_key=api_key)
            logger.debug(debug_message)

    tiid = item_module.get_tiid_by_alias(namespace, nid, mydao)
    if not tiid:
        if not debug_message:
            debug_message = "Item not in database. Call POST to register it"
        # if registration failure, report that info. Else suggest they register.
        abort(404, debug_message)
    return get_item_from_tiid(tiid, format, include_history)


'''GET /item/:tiid
404 if tiid not found in db
'''
@app.route('/item/<tiid>', methods=['GET'])
def get_item_from_tiid(tiid, format=None, include_history=False):

    try:
        item = item_module.get_item(tiid, myrefsets, mydao, include_history)
    except (LookupError, AttributeError):
        abort(404)

    if not item:
        abort(404)

    if item_module.is_currently_updating(tiid, myredis):
        response_code = 210 # not complete yet
        item["currently_updating"] = True
    else:
        response_code = 200
        item["currently_updating"] = False

    api_key = request.args.get("key", None)
    clean_item = item_module.clean_for_export(item, api_key, os.getenv("API_KEY"))
    resp = make_response(json.dumps(clean_item, sort_keys=True, indent=4),
                         response_code)
    resp.mimetype = "application/json"

    return resp


@app.route('/provider', methods=['GET'])
@app.route('/v1/provider', methods=['GET'])
def provider():
    ret = ProviderFactory.get_all_metadata()
    resp = make_response(json.dumps(ret, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"

    return resp

@app.route('/provider/<provider_name>/memberitems', methods=['POST'])
@app.route('/v1/provider/<provider_name>/memberitems', methods=['POST'])
def provider_memberitems(provider_name):
    """
    Make a file into a dict strings describing items.
    """

    file = request.files['file']
    logger.debug("In"+provider_name+"/memberitems, got file: filename="+file.filename)
    entries_str = file.read().decode("utf-8")

    provider = ProviderFactory.get_provider(provider_name)
    items_dict = provider.parse(entries_str)

    resp = make_response(json.dumps(items_dict), 200) # created
    resp.mimetype = "application/json"
    resp.headers['Access-Control-Allow-Origin'] = "*"
    return resp

@app.route("/provider/<provider_name>/memberitems/<query>", methods=['GET'])
@app.route("/v1/provider/<provider_name>/memberitems/<query>", methods=['GET'])
def provider_memberitems_get(provider_name, query):
    """
    Gets aliases associated with a query from a given provider.
    """

    try:
        provider = ProviderFactory.get_provider(provider_name)
        ret = provider.member_items(query)
    except ProviderItemNotFoundError:
        abort(404)
    except (ProviderTimeout, ProviderServerError):
        abort(503)  # crossref lookup error, might be transient
    except ProviderError:
        abort(500)

    resp = make_response(
        json.dumps({"memberitems":ret}, sort_keys=True, indent=4),
        200
    )
    resp.mimetype = "application/json"
    resp.headers['Access-Control-Allow-Origin'] = "*"
    return resp




'''
GET /collection/:collection_ID
returns a collection object and the items
'''
@app.route('/collection/<cid>', methods=['GET'])
@app.route('/v1/collection/<cid>', methods=['GET'])
@app.route('/collection/<cid>.<format>', methods=['GET'])
@app.route('/v1/collection/<cid>.<format>', methods=['GET'])
def collection_get(cid='', format="json", include_history=False):
    coll = mydao.get(cid)
    if not coll:
        abort(404)

    # if not include items, then just return the collection straight from couch
    if (request.args.get("include_items") in ["0", "false", "False"]):
        # except if format is csv.  can't do that.
        if format == "csv":
            abort(405)  # method not supported
        else:
            response_code = 200
            resp = make_response(json.dumps(coll, sort_keys=True, indent=4),
                                 response_code)
            resp.mimetype = "application/json"
    else:
        try:
            include_history = (request.args.get("include_history", 0) in ["1", "true", "True"])
            (coll_with_items, something_currently_updating) = collection.get_collection_with_items_for_client(cid, myrefsets, myredis, mydao, include_history)
        except (LookupError, AttributeError):  
            logger.error("couldn't get tiids for GET collection '{cid}'".format(cid=cid))
            abort(404)  # not found

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

            secret_key = os.getenv("API_KEY")  #ideally rename this to API_ADMIN_KEY
            if request.args.get("api_admin_key"):
                supplied_key = request.args.get("api_admin_key", "")
            else:
                supplied_key = request.args.get("key", "")

            clean_if_necessary_items = [item_module.clean_for_export(item, supplied_key, secret_key)
                for item in coll_with_items["items"]]

            coll_with_items["items"] = clean_if_necessary_items
            resp = make_response(json.dumps(coll_with_items, sort_keys=True, indent=4),
                                 response_code)
            resp.mimetype = "application/json"
    return resp


def get_coll_with_authentication_check(request, cid):
    coll = dict(mydao.db[cid])

    # if admin override key, then everything is fine
    if request.args.get("api_admin_key"):
        supplied_key = request.args.get("api_admin_key", "")
        secret_key = os.getenv("API_KEY")  #ideally rename this to API_ADMIN_KEY
        if secret_key == supplied_key:
            return coll

    # otherwise require authentication
    key = request.args.get("edit_key", None)
    if key is None:
        abort(404, "This method requires an update key.")

    if "key" in coll.keys():
        if coll["key"] != key:
            abort(403, "Wrong update key")
    elif "key_hash" in coll.keys():
        if not check_password_hash(coll["key_hash"], key):
            abort(403, "Wrong update key")
    else:
        abort(501, "This collection has no update key; it cant' be changed.")

    return coll

@app.route('/collection/<cid>/items', methods=['POST'])
@app.route('/v1/collection/<cid>/items', methods=['POST'])
def delete_and_put_helper(cid=""):
    """
    Lets browsers who can't do PUT or DELETE fake it with a POST
    """
    http_method = request.args.get("http_method", "")
    if http_method.lower() == "delete":
        return delete_items(cid)
    elif http_method.lower() == "put":
        return put_collection(cid)
    else:
        abort(404, "You must specify a valid HTTP method (POST or PUT) with the"
                   " http_method argument.")


@app.route('/collection/<cid>/items', methods=['DELETE'])
@app.route('/v1/collection/<cid>/items', methods=['DELETE'])
def delete_items(cid=""):
    """
    Deletes items from a collection
    """
    coll = get_coll_with_authentication_check(request, cid)

    try:
        new_alias_tiids = {}
        for alias, tiid in coll["alias_tiids"].iteritems():
            if tiid not in request.json["tiids"]:
                new_alias_tiids[alias] = tiid

        coll["alias_tiids"] = new_alias_tiids

    except (AttributeError, TypeError, KeyError) as e:
        # we got missing or improperly formated data.
        logger.error(
            "DELETE /collection/{id}/items threw an error: '{error_str}'. input: {json}.".format(
                id=coll["_id"],
                error_str=e,
                json=request.json))
        abort(404, "Missing arguments.")

    coll["last_modified"] = datetime.datetime.now().isoformat()
    mydao.db.save(coll)

    resp = make_response(json.dumps(coll, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


@app.route("/collection/<cid>/items", methods=["PUT"])
@app.route("/v1/collection/<cid>/items", methods=["PUT"])
def put_collection(cid=""):
    """
    Adds new items to a collection.
    """

    coll = get_coll_with_authentication_check(request, cid)

    try:
        aliases = request.json["aliases"]
        try:
            alias_strings = [namespace+":"+nid for (namespace, nid) in aliases]
        except TypeError:
            # jsonify the biblio dicts
            alias_strings = [namespace+":"+json.dumps(nid) for (namespace, nid) in aliases]

        (tiids, new_items) = item_module.create_or_update_items_from_aliases(
            aliases, myredis, mydao)

        # pretty sure this is putting the wrong tiids with the aliases...
        new_alias_tiids = dict(zip(alias_strings, tiids))

        coll["alias_tiids"].update(new_alias_tiids)

    except (AttributeError, TypeError) as e:
        # we got missing or improperly formated data.
        logger.error(
            "PUT /collection/{id}/items threw an error: '{error_str}'. input: {json}.".format(
                id=coll["_id"],
                error_str=e,
                json=request.json))
        abort(404, "Missing arguments.")

    coll["last_modified"] = datetime.datetime.now().isoformat()
    mydao.db.save(coll)

    resp = make_response(json.dumps(coll, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"

    return resp


""" Updates all the items in a given collection.
"""
@app.route("/collection/<cid>", methods=["POST"])
@app.route("/v1/collection/<cid>", methods=["POST"])
# not officially supported in api
def collection_update(cid=""):

    # first, get the tiids in this collection:
    try:
        collection = mydao.get(cid)
        tiids = collection["alias_tiids"].values()
    except Exception:
        logger.exception("couldn't get tiids in POST collection '{cid}'".format(
            cid=cid
        ))
        abort(404, "couldn't get tiids for this collection...maybe doesn't exist?")

    item_module.start_item_update(tiids, myredis, mydao)

    resp = make_response("true", 200)
    resp.mimetype = "application/json"
    return resp



# creates a collection with aliases
@app.route('/collection', methods=['POST'])
@app.route('/v1/collection', methods=['POST'])
def collection_create():
    """
    POST /collection
    creates new collection
    """
    response_code = None
    coll, key = collection.make(request.json.get("owner", None))
    refset_metadata = request.json.get("refset_metadata", None)
    if refset_metadata:
        coll["refset_metadata"] = refset_metadata
    coll["ip_address"] = request.remote_addr
    try:
        coll["title"] = request.json["title"]
        aliases = request.json["aliases"]
        (tiids, new_items) = item_module.create_or_update_items_from_aliases(aliases, myredis, mydao)
        for item in new_items:
            namespaces = item["aliases"].keys()

        if not tiids:
            abort(404, "POST /collection requires a list of [namespace, id] pairs.")
    except (AttributeError, TypeError):
        # we got missing or improperly formated data.
        logger.error(
            "we got missing or improperly formated data: '{id}' with {json}.".format(
                id=coll["_id"],
                json=str(request.json)))
        abort(404, "Missing arguments.")

    try:
        alias_strings = aliases_strings = [namespace+":"+nid for (namespace, nid) in aliases]
    except TypeError:
        # jsonify the biblio dicts
        alias_strings = aliases_strings = [namespace+":"+json.dumps(nid) for (namespace, nid) in aliases]

    # save dict of alias:tiid
    coll["alias_tiids"] = dict(zip(aliases_strings, tiids))

    logger.info(json.dumps(coll, sort_keys=True, indent=4))

    mydao.save(coll)
    response_code = 201 # Created
    logger.info(
        "saved new collection '{id}' with {num_items} items.".format(
            id=coll["_id"],
            num_items=len(coll["alias_tiids"])
        ))

    resp = make_response(json.dumps({"collection":coll, "key":key},
            sort_keys=True, indent=4), response_code)
    resp.mimetype = "application/json"
    return resp


# for internal use only
@app.route('/test/collection/<action_type>', methods=['GET'])
def tests_interactions(action_type=''):
    logger.info("getting test/collection/" + action_type)

    report = myredis.hgetall("test.collection." + action_type)
    report["url"] = "http://{root}/collection/{collection_id}".format(
        root=os.getenv("WEBAPP_ROOT"),
        collection_id=report["result"]
    )

    return render_template(
        'interaction_test_report.html',
        report=report
    )

# for internal use only
@app.route("/collections/recent")
@app.route("/collections/recent.<format>")
def latest_collections(format=""):
    res = mydao.db.view("queues/latest-collections", descending=True)
    if request.args.get('include_tests') in [1, "yes", "true", "True"]:
        include_tests = 1
    else:
        include_tests = 0

    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    rows = res[[include_tests, "zzz"]:[include_tests ,yesterday.isoformat()]].rows
    for row in rows:
        row["url"] = "http://{root}/collection/{collection_id}".format(
            root=os.getenv("WEBAPP_ROOT"),
            collection_id=row["id"]
        )

    if format == "html":
        resp = render_template("latest_collections.html", rows=rows)
    else:
        resp = make_response(json.dumps(rows, indent=4), 200)
        resp.mimetype = "application/json"

    return resp            


@app.route("/collections/<cids>")
@app.route("/v1/collections/<cids>")
def get_collection_titles(cids=''):
    from time import sleep
    sleep(1)
    cids_arr = cids.split(",")
    coll_info = collection.get_titles(cids_arr, mydao)
    resp = make_response(json.dumps(coll_info, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


@app.route("/collections/reference-sets")
@app.route("/v1/collections/reference-sets")
def reference_sets():
    resp = make_response(json.dumps(myrefsets, indent=4), 200)
    resp.mimetype = "application/json"
    return resp

@app.route("/collections/reference-sets-histograms")
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

    password = meta["password"]
    del(meta["password"])
    if password != os.getenv("API_KEY"):
        abort(403)

    prefix = meta["prefix"]
    del(meta["prefix"])

    max_registered_items = meta["max_registered_items"]
    del(meta["max_registered_items"])

    new_api_key = api_user.save_api_user(prefix, max_registered_items, mypostgresdao, **meta)

    resp = make_response(json.dumps({"api_key":new_api_key}, indent=4), 200)
    resp.mimetype = "application/json"
    return resp

@app.route("/user/<userid>", methods=["GET"])
@app.route("/v1/user/<userid>", methods=["GET"])
def get_user(userid=''):
    """
    GET /user
    Gets a user.

    The user's private properties are not returned unless you pass a correct collection key.
    """

    key = request.args.get("key")
    try:
        user = UserFactory.get(userid, mydao, key)
    except KeyError:
        abort(404, "User doesn't exist.")
    except NotAuthenticatedError:
        abort(403, "You've got the wrong password.")

    resp = make_response(json.dumps(user, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


@app.route('/user', methods=['PUT'])
@app.route('/v1/user', methods=['PUT'])
def update_user(userid=''):
    """
    PUT /user
    creates new user
    """

    new_stuff = request.json
    try:
        key = new_stuff["key"]
    except KeyError:
        abort(400, "the submitted user object is missing required properties.")
    try:
        res = UserFactory.put(new_stuff, key, mydao)
    except NotAuthenticatedError:
        abort(403, "You've got the wrong password.")
    except AttributeError:
        abort(400, "the submitted user object is missing required properties.")

    resp = make_response(json.dumps(res, indent=4), 200)
    resp.mimetype = "application/json"
    return resp

# can remove this wrapper and just use mypostgresdao version once finished with couchdb
def save_email(payload):
    doc_id = shortuuid.uuid()[0:24]
    doc = {"_id":doc_id, 
            "type":"email", 
            "created":datetime.datetime.now().isoformat(),
            "payload":payload}
    mydao.save(doc)
    mypostgresdao.save_email(doc)
    return doc_id

GOOGLE_SCHOLAR_CONFIRM_PATTERN = re.compile("""for the query:\nNew articles in (?P<name>.*)'s profile\n\nClick to confirm this request:\n(?P<url>.*)\n\n""")
def alert_if_google_scholar_notification_confirmation(payload):
    name = None
    url = None
    try:
        email_body = payload["plain"]
        match = GOOGLE_SCHOLAR_CONFIRM_PATTERN.search(email_body)
        if match:
            url = match.group("url")
            name = match.group("name")
            logger.info("Google Scholar notification confirmation for {name} is at {url}".format(
                name=name, url=url))
    except (KeyError, TypeError):
        pass
    return(name, url)

GOOGLE_SCHOLAR_NEW_ARTICLES_PATTERN = re.compile("""Scholar Alert - (?P<name>.*) - new articles""")
def alert_if_google_scholar_new_articles(payload, doc_id):
    name = None
    try:
        subject = payload["headers"]["Subject"]
        match = GOOGLE_SCHOLAR_NEW_ARTICLES_PATTERN.search(subject)
        if match:
            name = match.group("name")
            logger.info("Just received Google Scholar alert: new articles for {name}, saved at {doc_id}".format(
                name=name, doc_id=doc_id))
    except (KeyError, TypeError):
        pass
    return(name)

# route to receive email
@app.route('/v1/inbox', methods=["POST"])
def inbox():
    payload = request.json
    doc_id = save_email(payload)
    logger.debug("You've got mail. Payload: {payload}".format(
        payload=payload))
    logger.info("You've got mail. Saved as {doc_id}. Subject: {subject}".format(
        doc_id=doc_id, subject=payload["headers"]["Subject"]))

    alert_if_google_scholar_notification_confirmation(payload)
    alert_if_google_scholar_new_articles(payload, doc_id)

    resp = make_response(json.dumps({"_id":doc_id}, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


try:
    # see http://support.blitz.io/discussions/problems/363-authorization-error
    @app.route('/mu-' + os.environ["BLITZ_API_KEY"], methods=["GET"])
    def blitz_validation():
        resp = make_response("42", 200)
        return resp
except KeyError:
    logger.error("BLITZ_API_KEY environment variable not defined, not setting up validation api endpoint")

@app.route('/hirefire/test', methods=["GET"])
def hirefire_test():
    resp = make_response("HireFire", 200)
    resp.mimetype = "text/html"
    return resp

try:
    @app.route('/hirefire/' + os.environ["HIREFIRE_TOKEN"] + '/info', methods=["GET"])
    def hirefire_worker_count():
        import time
        time.sleep(3)

        resp = make_response(json.dumps([{"worker":1}]), 200)
        resp.mimetype = "application:json"
        return resp
except KeyError:
    logger.error("HIREFIRE_TOKEN environment variable not defined, not setting up validation api endpoint")


@app.route('/hirefireapp/test', methods=["GET"])
def hirefireapp_test():
    resp = make_response("HireFire", 200)
    resp.mimetype = "text/html"
    return resp

try:
    @app.route('/hirefireapp/' + os.environ["HIREFIREAPP_TOKEN"] + '/info', methods=["GET"])
    def hirefireapp_worker_count():
        resp = make_response(json.dumps({"worker":1}), 200)
        resp.mimetype = "application:json"
        return resp
except KeyError:
    logger.error("HIREFIREAPP_TOKEN environment variable not defined, not setting up validation api endpoint")


