from flask import json, request, abort, make_response
from flask import render_template
import os, datetime, re, couchdb
from werkzeug.security import check_password_hash
from collections import defaultdict
import rq

import newrelic.agent
mynewrelic_application = newrelic.agent.application('total-impact-core')

from totalimpact import dao, app, tiredis, collection, tiqueue
from totalimpact.models import ItemFactory, MemberItems, UserFactory, NotAuthenticatedError
from totalimpact.providers.provider import ProviderFactory, ProviderItemNotFoundError, ProviderError
from totalimpact import default_settings
import logging

# temporary, do it here for experimenting


logger = logging.getLogger("ti.views")
logger.setLevel(logging.DEBUG)

mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.getenv("CLOUDANT_DB"))
myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))
myrq = rq.Queue("alias", connection=myredis)

logger.debug("Building reference sets")
myrefsets = None
try:
    myrefsets = collection.build_all_reference_lookups(myredis, mydao)
    logger.debug("Reference sets dict has %i keys" %len(myrefsets.keys()))
except (couchdb.ResourceNotFound, LookupError, AttributeError), e:
    logger.error("Exception %s: Unable to load reference sets" % (e.__repr__()))


# setup to remove control characters from received IDs
# from http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))
def clean_id(nid):
    nid = control_char_re.sub('', nid)
    nid = nid.replace(u'\u200b', "")
    nid = nid.strip()
    return(nid)

def set_db(url, db):
    """useful for unit testing, where you want to use a local database
    """
    global mydao 
    mydao = dao.Dao(url, db)
    return mydao


#@app.before_request
def check_api_key():
    ti_api_key = request.values.get('api_key', '')
    logger.debug("In check_api_key with " + ti_api_key)
    if not ti_api_key:
        response = make_response(
            "please get an api key and include api_key=YOURKEY in your query",
            403)
        return response


@app.after_request
def add_crossdomain_header(resp):
    resp.headers['Access-Control-Allow-Origin'] = "*"
    resp.headers['Access-Control-Allow-Methods'] = "POST, GET, OPTIONS, PUT, DELETE"
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
    resp = make_response(json.dumps(msg, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


def get_tiid_by_alias(ns, nid):
    res = mydao.view('queues/by_alias')

    matches = res[[ns,
                   nid]] # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults

    if matches.rows:
        if len(matches.rows) > 1:
            logger.warning("More than one tiid for alias (%s, %s)" % (ns, nid))
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
    resp = make_response(json.dumps(tiid, sort_keys=True, indent=4), 303)
    resp.mimetype = "application/json"
    return resp


def create_item(namespace, nid):
    logger.debug("In create_item with alias" + str((namespace, nid)))
    item = ItemFactory.make()

    # set this so we know when it's still updating later on
    myredis.set_num_providers_left(
        item["_id"],
        ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
    )

    item["aliases"][namespace] = [nid]
    mydao.save(item)
    myrq.enqueue(tiqueue.update_item, item)

    logger.info("Created new item '{id}' with alias '{alias}'".format(
        id=item["_id"],
        alias=str((namespace, nid))
    ))

    try:
        return item["_id"]
    except AttributeError:
        abort(500)


def create_or_find_items_from_aliases(clean_aliases):
    tiids = []
    items = []
    for alias in clean_aliases:
        (namespace, nid) = alias
        existing_tiid = get_tiid_by_alias(namespace, nid)
        if existing_tiid:
            tiids.append(existing_tiid)
            logger.debug("found an existing tiid ({tiid}) for alias {alias}".format(
                    tiid=existing_tiid,
                    alias=str(alias)
                ))
        else:
            logger.debug("alias {alias} isn't in the db; making a new item for it.".format(
                    alias=alias
                ))
            item = ItemFactory.make()
            item["aliases"][namespace] = [nid]
            myrq.enqueue(tiqueue.update_item, item)
            items.append(item)
            tiids.append(item["_id"])    
    return(tiids, items)


def prep_collection_items(aliases):
    logger.info("got a list of aliases; creating new items for them.")
    try:
        # remove unprintable characters and change list to tuples
        clean_aliases = [(clean_id(namespace), clean_id(nid)) for [namespace, nid] in aliases]
    except ValueError:
        logger.error("bad input to POST /collection (requires [namespace, id] pairs):{input}".format(
                input=str(clean_aliases)
            ))
        abort(404, "POST /collection requires a list of [namespace, id] pairs.")

    logger.debug("POST /collection got list of aliases; creating new items for {aliases}".format(
            aliases=str(clean_aliases)
        ))

    (tiids, items) = create_or_find_items_from_aliases(clean_aliases)

    logger.debug("POST /collection saving a group of {num} new items: {items}".format(
            num=len(items),
            items=str(items)
        ))

    # for each item, set the number of providers that need to run before the update is done
    for item in items:
        myredis.set_num_providers_left(
            item["_id"],
            ProviderFactory.num_providers_with_metrics(
                default_settings.PROVIDERS)
        )

    # batch upload the new docs to the db
    for doc in mydao.db.update(items):
        pass

    return tiids


@app.route('/item/<namespace>/<path:nid>', methods=['POST'])
def item_namespace_post(namespace, nid):
    """Creates a new item using the given namespace and id.

    POST /item/:namespace/:nid
    201 location: {tiid}
    500?  if fails to create
    example /item/PMID/234234232
    """
    # remove unprintable characters
    nid = clean_id(nid)

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
        item = ItemFactory.get_item(tiid, myrefsets, mydao)
    except (LookupError, AttributeError):
        abort(404)

    if not item:
        abort(404)

    if myredis.get_num_providers_left(tiid) > 0:
        response_code = 210 # not complete yet
        item["currently_updating"] = True
    else:
        response_code = 200
        item["currently_updating"] = False

    resp = make_response(json.dumps(item, sort_keys=True, indent=4),
                         response_code)
    resp.mimetype = "application/json"

    return resp


@app.route('/provider', methods=['GET'])
def provider():
    ret = ProviderFactory.get_all_metadata()
    resp = make_response(json.dumps(ret, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"

    return resp


'''
GET /provider/:provider/memberitems?query=:querystring[&type=:type]
returns member ids associated with the group in a json list of (key, value) pairs like [(namespace1, id1), (namespace2, id2)] 
of type :type (when this needs disambiguating)
if > 100 memberitems, return the first 100 with a response code that indicates the list has been truncated
examples : /provider/github/memberitems?query=jasonpriem&type=github_user

'''

@app.route('/provider/<provider_name>/memberitems', methods=['POST'])
def provider_memberitems(provider_name):
    """
    Starts a memberitems update for a specified provider, using a supplied file.

    Returns a hash of the file's contents, which is needed to get memberitems'
    output. To get output, poll GET /provider/<provider_name>/memberitems/<hash>?method=async
    """
    logger.debug("Query POSTed to {provider_name}/memberitems with request headers '{headers}'".format(
        provider_name=provider_name,
        headers=request.headers
    ))

    file = request.files['file']
    logger.debug("In provider_memberitems got file")
    logger.debug("filename = " + file.filename)
    query = file.read().decode("utf-8")

    provider = ProviderFactory.get_provider(provider_name)
    memberitems = MemberItems(provider, myredis)
    query_hash = memberitems.start_update(query)

    resp = make_response('"'+query_hash+'"', 201) # created
    resp.mimetype = "application/json"
    resp.headers['Access-Control-Allow-Origin'] = "*"
    return resp


@app.route("/provider/<provider_name>/memberitems/<query>", methods=['GET'])
def provider_memberitems_get(provider_name, query):
    """
    Gets aliases associated with a query from a given provider.

    method=sync will call a provider's memberitems method with the supplied query,
                and wait for the result.
    method=async will look up the query in total-impact's db and return the current
                 status of that query.

    """
    provider = ProviderFactory.get_provider(provider_name)
    memberitems = MemberItems(provider, myredis)

    try:
        ret = getattr(memberitems, "get_"+request.args.get('method', "sync"))(query)
    except ProviderItemNotFoundError:
        abort(404)
    except ProviderError:
        abort(500)

    resp = make_response(json.dumps(ret, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"
    resp.headers['Access-Control-Allow-Origin'] = "*"
    return resp


# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/dryad/aliases/10.5061/dryad.7898
@app.route('/provider/<provider_name>/aliases/<path:id>', methods=['GET'])
def provider_aliases(provider_name, id):
    provider = ProviderFactory.get_provider(provider_name)
    if id == "example":
        id = provider.example_id[1]
        url = "http://localhost:8080/" + provider_name + "/aliases?%s"
    else:
        url = None

    try:
        new_aliases = provider._get_aliases_for_id(id, url, cache_enabled=False)
    except NotImplementedError:
        new_aliases = []

    all_aliases = [(provider.example_id[0], id)] + new_aliases

    resp = make_response(json.dumps(all_aliases, sort_keys=True, indent=4))
    resp.mimetype = "application/json"

    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/dryad/metrics/10.5061/dryad.7898
@app.route('/provider/<provider_name>/metrics/<path:id>', methods=['GET'])
def provider_metrics(provider_name, id):
    provider = ProviderFactory.get_provider(provider_name)
    if id == "example":
        id = provider.example_id[1]
        url = "http://localhost:8080/" + provider_name + "/metrics?%s"
    else:
        url = None

    metrics = provider.get_metrics_for_id(id, url, cache_enabled=False)

    resp = make_response(json.dumps(metrics, sort_keys=True, indent=4))
    resp.mimetype = "application/json"

    return resp

# For internal use only.  Useful for testing before end-to-end working
# Example: http://127.0.0.1:5001/provider/dryad/biblio/10.5061/dryad.7898
@app.route('/provider/<provider_name>/biblio/<path:id>', methods=['GET'])
def provider_biblio(provider_name, id):
    provider = ProviderFactory.get_provider(provider_name)
    if id == "example":
        id = provider.example_id[1]
        url = "http://localhost:8080/" + provider_name + "/biblio?%s"
    else:
        url = None

    biblio = provider.get_biblio_for_id(id, url, cache_enabled=False)
    resp = make_response(json.dumps(biblio, sort_keys=True, indent=4))
    resp.mimetype = "application/json"

    return resp


'''
GET /collection/:collection_ID
returns a collection object and the items
'''
@app.route('/collection/<cid>', methods=['GET'])
@app.route('/collection/<cid>.<format>', methods=['GET'])
def collection_get(cid='', format="json"):
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
            (coll_with_items, something_currently_updating) = collection.get_collection_with_items_for_client(cid, myrefsets, myredis, mydao)
        except (LookupError, AttributeError):  
            logger.error("couldn't get tiids for collection '{cid}'".format(cid=cid))
            abort(404)  # not found

        # return success if all reporting is complete for all items    
        if something_currently_updating:
            response_code = 210 # update is not complete yet
        else:
            response_code = 200

        if format == "csv":
            items = coll_with_items["items"]
            csv = collection.make_csv_stream(items)
            resp = make_response(csv, response_code)
            resp.mimetype = "text/csv;charset=UTF-8"
            resp.headers.add("Content-Disposition",
                             "attachment; filename=ti.csv")
            resp.headers.add("Content-Encoding",
                             "UTF-8")
        else:
            resp = make_response(json.dumps(coll_with_items, sort_keys=True, indent=4),
                                 response_code)
            resp.mimetype = "application/json"
    return resp

@app.route("/collection/<cid>", methods=["PUT"])
def put_collection(cid=""):
    key = request.args.get("key", None)
    if key is None:
        abort(404, "This method requires an update key.")

    coll = dict(mydao.db[cid])
    if "key_hash" not in coll.keys():
        abort(501, "This collection has no update key; it cant' be changed.")
    if not check_password_hash(coll["key_hash"], key):
        abort(403, "Wrong update key")

    for k in ["title", "owner", "alias_tiids"]:
        try:
            coll[k] = request.json[k]
        except KeyError:
            pass

    coll["last_modified"] = datetime.datetime.now().isoformat()
    print coll
    mydao.db.save(coll)

    # expire it from redis
    myredis.expire_collection(cid)

    resp = make_response(json.dumps(coll, sort_keys=True, indent=4), 200)
    resp.mimetype = "application/json"
    return resp



@app.route("/collection/<cid>", methods=["POST"])
def collection_update(cid=""):
    """ Updates all the items in a given collection.
    """

    # first, get the tiids in this collection:
    try:
        collection = mydao.get(cid)
        tiids = collection["alias_tiids"].values()
    except Exception:
        logger.exception("couldn't get tiids for collection '{cid}'".format(
            cid=cid
        ))
        abort(404, "couldn't get tiids for this collection...maybe doesn't exist?")

    # expire it from redis
    myredis.expire_collection(cid)

    mynewrelic_application.record_metric("Custom/Collection/Update", 1)

    # put each of them on the update queue
    for tiid in tiids:
        logger.debug("In update_item with tiid " + tiid)

        # set this so we know when it's still updating later on
        myredis.set_num_providers_left(
            tiid,
            ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
        )

        item_doc = mydao.get(tiid)
        myrq.enqueue(tiqueue.update_item, item_doc)

    resp = make_response("true", 200)
    resp.mimetype = "application/json"
    return resp



# creates a collectino with aliases
@app.route('/collection', methods=['POST'])
def collection_create():
    """
    POST /collection
    creates new collection
    """
    response_code = None
    coll, key = collection.make(owner=request.json.get("owner", None))
    coll["ip_address"] = request.remote_addr
    try:
        coll["title"] = request.json["title"]
        aliases = request.json["aliases"]
        tiids = prep_collection_items(aliases)
        aliases_strings = [namespace+":"+nid for (namespace, nid) in aliases]
    except (AttributeError, TypeError):
        # we got missing or improperly formated data.
        logger.error(
            "we got missing or improperly formated data: '{id}' with {json}.".format(
                id=coll["_id"],
                json=str(request.json)))
        abort(404, "Missing arguments.")

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
def get_collection_titles(cids=''):
    from time import sleep
    sleep(1)
    cids_arr = cids.split(",")
    coll_info = collection.get_titles(cids_arr, mydao)
    resp = make_response(json.dumps(coll_info, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


@app.route("/collections/reference-sets")
def reference_sets():
    resp = make_response(json.dumps(myrefsets, indent=4), 200)
    resp.mimetype = "application/json"
    return resp


@app.route("/user/<userid>", methods=["GET"])
def get_user(userid=''):
    """
    GET /user
    Gets a user.

    The user's private properties are not returned unless you pass a correct key.
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
def update_user(userid=''):
    """
    PUT /collection
    creates new collection
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

