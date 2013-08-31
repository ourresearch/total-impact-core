import couchdb, os, logging, sys, collections
from pprint import pprint
import time, datetime, json
import requests
import argparse

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
 

def item_action_on_a_page(page):
    items = [row.doc for row in page]

    alias_tuples_to_commit = {}
    for item_doc in items:
        new_item_object = item_module.create_objects_from_item_doc(item_doc, alias_tuples_to_commit)
        print item_doc["_id"], len(new_item_object.aliases)
    db.session.commit()
    db.session.flush()
    return


def collection_action_on_a_page(page):
    collections = [row.doc for row in page]

    collection_tiids_to_commit = {}
    added_items_to_commit = {}
    for coll_doc in collections:
        new_coll_object = collection.create_objects_from_collection_doc(coll_doc, collection_tiids_to_commit, added_items_to_commit)
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



def run_through_items(startkey="00000", page_size=100):
    myview_name = "temp/by_type_and_id"
    mystart_key = ["item", startkey]
    myend_key = ["item", "zzzzzzzz"]

    now = datetime.datetime.now().isoformat()

    run_on_documents(item_action_on_a_page, 
        view_name=myview_name, 
        start_key=mystart_key, 
        end_key=myend_key, 
        page_size=page_size)


def run_through_collections(startkey="00000", page_size=100):
    myview_name = "temp/by_type_and_id"
    mystart_key = ["collection", startkey]
    myend_key = ["collection", "zzzzzzzz"]

    now = datetime.datetime.now().isoformat()

    run_on_documents(collection_action_on_a_page, 
        view_name=myview_name, 
        start_key=mystart_key, 
        end_key=myend_key, 
        page_size=page_size)


def setup_postgres(drop_all=False):

    # set up postgres
    logger.info("connecting to postgres")

    #export POSTGRESQL_URL=postgres://localhost/core_migration
    #export POSTGRESQL_URL=postgres://localhost/corecopy

    if "def95794hs4ou7" in app.config["SQLALCHEMY_DATABASE_URI"]:
        print "\n\nTHIS MAY BE THE PRODUCTION DATABASE!!!"
        confirm = raw_input("\nType YES if you are sure you want to run this test:")
        if not confirm=="YES":
            print "nevermind, then."
            exit()

    if drop_all:
        print "the postgres database is ", app.config["SQLALCHEMY_DATABASE_URI"]
        confirm = raw_input("\nType YES if you are sure you want to drop tables:")
        if not confirm=="YES":
            print "nevermind, then."
            exit()
        try:
            db.drop_all()
        except OperationalError, e:  #database "database" does not exist
            print e
    db.create_all()
    logger.info("connected to postgres {uri}".format(
        uri=app.config["SQLALCHEMY_DATABASE_URI"]))


def setup_couch():
    # set up couchdb
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")

    # do a few preventative checks
    if (cloudant_db == "ti"):
        print "\n\nTHIS MAY BE THE PRODUCTION DATABASE!!!"
        confirm = raw_input("\nType YES if you are sure you want to run this test:")
        if not confirm=="YES":
            print "nevermind, then."
            exit()
    else:
        print "\n\nThis doesn't appear to be the production database\n\n"

    couch = couchdb.Server(url=cloudant_url)
    couch_db = couch[cloudant_db]
    print couch_db
    logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

    return couch_db



if __name__ == "__main__":
    # get args from the command line:
    parser = argparse.ArgumentParser(description="copy data from couch into postgres")
    parser.add_argument('--drop', 
        default=False,
        action='store_true', 
        help="drop tables before creating them")
    parser.add_argument('--collections', 
        default=False,
        action='store_true', 
        help="iterate over collections, copying collections and their related info (collection tiids, added_items)")
    parser.add_argument('--items', 
        default=False,
        action='store_true', 
        help="iterate over items, copying items and their related info (biblio, metrics, aliases)")
    parser.add_argument('--pagesize', 
        default=100,
        type=int,
        help="number of documents to get from couch in each batch")
    parser.add_argument('--items_startkey', 
        default="000000",
        type=str,
        help="id to start the item view")
    parser.add_argument('--collections_startkey', 
        default="000000",
        type=str,
        help="id to start the collection view")
    args = vars(parser.parse_args())
    print args
    print "postgres_sqlalchemy_move.py starting."

    setup_postgres(drop_all=args["drop"])
    couch_db = setup_couch()
    if args["collections"]:
        run_through_collections(args["collections_startkey"], args["pagesize"])
    if args["items"]:
        run_through_items(args["items_startkey"], args["pagesize"])

    db.session.close_all()

  

