import couchdb, os, logging, sys, collections
from pprint import pprint
import time, datetime, json
import requests

from couch_paginator import CouchPaginator
from totalimpact import dao
import psycopg2
from sqlalchemy.exc import OperationalError

from totalimpact import db, app
from totalimpact import collection
from totalimpact.collection import Collection, CollectionTiid, AddedItem
from totalimpact import item as item_module
from totalimpact.item import Item, Alias, Metric, Biblio

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/db_housekeeping/postgres_mirror.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("postgres_sqlalchemy_move")
 


def create_alias_objects(alias_tuples, created, tuples_to_commit, skip_biblio=True):
    new_alias_objects = []

    for alias_tuple in alias_tuples:
        try:
            alias_tuple = item_module.canonical_alias_tuple(alias_tuple)
            (namespace, nid) = alias_tuple
        except ValueError:
            print "FAIL to parse, skipping ", alias_tuple, created[0:10]
            continue

        if skip_biblio and (namespace=="biblio"):
            # don't bother saving it
            continue

        if not nid:
            print "FAIL no nid, skipping ", alias_tuple, created[0:10]
            continue

        try:
            alias_object = Alias.filter_by_alias(alias_tuple).first()
        except TypeError:
            alias_object = None

        alias_key = ":".join(alias_tuple)
        if alias_object:
            pass
        elif alias_key in tuples_to_commit:
            alias_object = tuples_to_commit[alias_key]
        else:
            alias_object = Alias(alias_tuple, created)
            tuples_to_commit[alias_key] = alias_object
            db.session.add(alias_object)

        new_alias_objects += [alias_object]    

    return (new_alias_objects, tuples_to_commit)


def create_collection_tiid_objects(tiids, created, collection_tiids_to_commit):
    new_tiid_objects = []

    for tiid in tiids:
        try:
            tiid_object = CollectionTiid.query.filter_by(tiid=tiid).first()
        except TypeError:
            tiid_object = None

        if tiid_object:
            pass
        elif tiid in collection_tiids_to_commit:
            tiid_object = collection_tiids_to_commit[tiid]
        else:
            tiid_object = CollectionTiid(tiid=tiid)
            collection_tiids_to_commit[tiid] = tiid_object
            db.session.add(tiid_object)

        new_tiid_objects += [tiid_object]    

    return (new_tiid_objects, collection_tiids_to_commit)


def create_added_item_objects(alias_tuples, cid, created, added_items_to_commit):
    new_added_item_objects = []

    for alias_tuple in alias_tuples:
        try:
            alias_tuple = item_module.canonical_alias_tuple(alias_tuple)
            (namespace, nid) = alias_tuple
        except ValueError:
            print "FAIL to parse, skipping ", alias_tuple, created[0:10]
            continue

        try:
            added_item_object = AddedItem.query.filter_by(namespace=namespace, nid=nid).first()
        except TypeError:
            added_item_object = None

        alias_key = ":".join(alias_tuple)
        if added_item_object:
            pass
        elif alias_key in added_items_to_commit:
            added_item_object = added_items_to_commit[alias_key]
        else:
            added_item_object = AddedItem(cid=cid, namespace=namespace, nid=nid, created=created)
            added_items_to_commit[alias_key] = added_item_object
            db.session.add(added_item_object)

        new_added_item_objects += [added_item_object]    

    return (new_added_item_objects, added_items_to_commit)


def create_metric_objects(item_object, old_style_metric_dict):
    new_metric_objects = []

    for full_metric_name in old_style_metric_dict:
        (provider, metric_name) = full_metric_name.split(":")
        metric_details = old_style_metric_dict[full_metric_name]
        new_style_metric_dict = {
            "metric_name": metric_name, 
            "provider": provider, 
            "drilldown_url": metric_details["provenance_url"]
        }

        for collected_date in metric_details["values"]["raw_history"]:
            new_style_metric_dict["collected_date"] = collected_date
            new_style_metric_dict["raw_value"] = metric_details["values"]["raw_history"][collected_date]
            metric_object = Metric(item_object, **new_style_metric_dict)

            new_metric_objects += [metric_object]    
            db.session.add(metric_object)

    return new_metric_objects


def create_biblio_objects(item_object, old_style_biblio_dict, provider="unknown"):
    new_biblio_objects = []

    for biblio_name in old_style_biblio_dict:
        biblio_object = Biblio(item_object, 
                biblio_name, 
                old_style_biblio_dict[biblio_name], 
                provider, 
                item_object.created)
        new_biblio_objects += [biblio_object] 
        db.session.add(biblio_object)

    return new_biblio_objects


def item_action_on_a_page(page):
    items = [row.doc for row in page]

    alias_tuples_to_commit = {}
    for item_doc in items:
        new_item_object = Item.query.filter_by(tiid=item_doc["_id"]).first()
        if not new_item_object:
            new_item_object = Item.create_from_old_doc(item_doc)
            db.session.add(new_item_object)

        alias_dict = item_doc["aliases"]
        alias_tuples = item_module.alias_tuples_from_dict(alias_dict)            
        (new_alias_objects, alias_tuples_to_commit) = create_alias_objects(alias_tuples, 
                item_doc["created"], 
                alias_tuples_to_commit, 
                skip_biblio=True)
        new_item_object.aliases = new_alias_objects

        # biblio within aliases
        if "biblio" in alias_dict:
            biblio_dicts = alias_dict["biblio"]
            provider_number = 0
            for biblio_dict in biblio_dicts:
                provider_number += 1
                new_biblio_objects = create_biblio_objects(new_item_object, 
                        biblio_dict, 
                        provider="unknown"+str(provider_number))
                new_item_object.biblios += new_biblio_objects

        # biblio within biblio
        # if "biblio" in item_doc:
        #     biblio_dict = item_doc["biblio"]
        #     new_biblio_objects = create_biblio_objects(new_item_object, biblio_dict) 
        #     new_item_object.biblios = new_biblio_objects

        if "metrics" in item_doc:
            metrics_dict = item_doc["metrics"]
            new_metric_objects = create_metric_objects(new_item_object, metrics_dict) 
            new_item_object.metrics = new_metric_objects


        print item_doc["_id"], len(new_item_object.aliases)
    db.session.commit()
    db.session.flush()
    return


def collection_action_on_a_page(page):
    collections = [row.doc for row in page]

    from totalimpact import collection, item as item_module
    collection_tiids_to_commit = {}
    added_items_to_commit = {}
    for coll_doc in collections:
        new_coll_object = Collection.query.filter_by(cid=coll_doc["_id"]).first()
        if not new_coll_object:
            new_coll_object = Collection.create_from_old_doc(coll_doc)
            db.session.add(new_coll_object)

        tiids = coll_doc["alias_tiids"].values()
        (new_tiid_objs, collection_tiids_to_commit) = create_collection_tiid_objects(tiids, 
            coll_doc["created"], 
            collection_tiids_to_commit)
        new_coll_object.tiids = new_tiid_objs

        alias_strings = coll_doc["alias_tiids"].keys()
        alias_tuples = [alias_string.split(":", 1) for alias_string in alias_strings]          
        (new_added_item_objects, added_items_to_commit) = create_added_item_objects(alias_tuples, 
            new_coll_object.cid,
            coll_doc["created"], 
            added_items_to_commit)
        new_coll_object.added_items = new_added_item_objects

        print coll_doc["_id"], len(new_coll_object.tiids)
    db.session.commit()
    db.session.flush()
    return


def run_on_documents(func_page, view_name, start_key, end_key, row_count=0, page_size=500):
    couch_page = CouchPaginator(couch_db, view_name, page_size, start_key=start_key, end_key=end_key, include_docs=True)

    while couch_page:
        func_page(couch_page)
        row_count += page_size

        logger.info("%i. getting new page" %(row_count))
        if couch_page.has_next:
            couch_page = CouchPaginator(couch_db, view_name, page_size, start_key=couch_page.next, end_key=end_key, include_docs=True)
        else:
            couch_page = None

    print "number items = ", row_count



def run_through_items():
    myview_name = "temp/by_type_and_id"
    mystart_key = ["item", "00000000"]
    myend_key = ["item", "zzzzzzzz"]

    now = datetime.datetime.now().isoformat()

    run_on_documents(item_action_on_a_page, 
        view_name=myview_name, 
        start_key=mystart_key, 
        end_key=myend_key, 
        page_size=100)


def run_through_collections():
    myview_name = "temp/by_type_and_id"
    mystart_key = ["collection", "0000000"]
    myend_key = ["collection", "zzzzzzzz"]

    now = datetime.datetime.now().isoformat()

    run_on_documents(collection_action_on_a_page, 
        view_name=myview_name, 
        start_key=mystart_key, 
        end_key=myend_key, 
        page_size=100)


def setup(drop_all=False):

    # set up postgres
    logger.info("connecting to postgres")

    #export POSTGRESQL_URL=postgres://localhost/core_migration
    #export POSTGRESQL_URL=postgres://localhost/corecopy

    #if not "localhost" in app.config["SQLALCHEMY_DATABASE_URI"]:
    #    assert(False), "Not running this unittest because SQLALCHEMY_DATABASE_URI is not on localhost"

    if drop_all:
        try:
            db.drop_all()
            pass
        except OperationalError, e:  #database "database" does not exist
            print e
            pass
    db.create_all()
    logger.info("connected to postgres")

    # set up couchdb
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")
    couch = couchdb.Server(url=cloudant_url)
    couch_db = couch[cloudant_db]
    logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

    # do a few preventative checks
    if (cloudant_db == "ti"):
        print "\n\nTHIS MAY BE THE PRODUCTION DATABASE!!!"
    else:
        print "\n\nThis doesn't appear to be the production database\n\n"
    confirm = None
    #confirm = raw_input("\nType YES if you are sure you want to run this test:")
    confirm = "YES"
    if not confirm=="YES":
        print "nevermind, then."
        exit()

    return couch_db



couch_db = setup(drop_all=False)

run_through_collections()
#run_through_items()

db.session.close_all()

  

