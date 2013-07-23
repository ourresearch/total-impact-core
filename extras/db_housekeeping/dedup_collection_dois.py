import couchdb, os, logging, sys, collections
from pprint import pprint
import time
import requests
import copy

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/db_housekeeping/dedup_collection_dois.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("dedup_collection_dois")
 
cloudant_db = os.getenv("CLOUDANT_DB")
cloudant_url = os.getenv("CLOUDANT_URL")

couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

def dedup_collections(collection_id):
    url = "http://{api_root}/v1/collection/{collection_id}?key=samplekey".format(
        api_root=os.getenv("API_ROOT"), collection_id=collection_id)
    print url
    try:
        r = requests.get(url, timeout=120)
    except requests.Timeout:
        print "timeout"
        return []
    try:
        collection = r.json
    except TypeError:
        print "TypeError" #unicode() argument 2 must be string, not None
        return

    if not collection:
        return
    items = collection["items"]

    unique_tiids = set()
    unique_dois = set()
    tiids_to_delete = []

    for item in items:
        try:
            dois = item["aliases"]["doi"]
            for doi in dois:
                if doi not in unique_dois:
                    unique_dois.add(doi)
                    unique_tiids.add(item["_id"])
        except KeyError:
            pass #no dois

    for item in items:
        if "doi" in item["aliases"]:
            if item["_id"] not in unique_tiids:
                tiids_to_delete += [item["_id"]]

    if tiids_to_delete:
        delete_tiids_from_collection(collection_id, tiids_to_delete)

def delete_tiids_from_collection(collection_id, tiids_to_delete):
    doc = db.get(collection_id)
    print "tiids_to_delete", tiids_to_delete
    for (alias, tiid) in doc["alias_tiids"].items():
        if tiid in tiids_to_delete:
            del doc["alias_tiids"][alias]
    db.save(doc)
    print "saved deduped collection", collection_id

def dedup_merged_collections():
    from totalimpact import item, tiredis

    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, include_docs=True)
    row_count = 0
    page_size = 500
    start_key = ["collection", "000"]
    end_key = ["collection", "00zz"]

    from couch_paginator import CouchPaginator
    page = CouchPaginator(db, view_name, page_size, include_docs=True, start_key=start_key, end_key=end_key)

    number_of_collections = {}
    size_of_collections = {}
    size_of_profile_collections = {}

    while page:
        for row in page:
            dedup_collections(row.id)
            #doc = row.doc

            row_count += 1
        logger.info("%i. getting new page, last id was %s" %(row_count, row.id))
        if page.has_next:
            page = CouchPaginator(db, view_name, page_size, start_key=page.next, end_key=end_key, include_docs=True)
        else:
            page = None

if (cloudant_db == "ti"):
    print "\n\nTHIS MAY BE THE PRODUCTION DATABASE!!!"
else:
    print "\n\nThis doesn't appear to be the production database"
confirm = None
confirm = raw_input("\nType YES if you are sure you want to run this test:")
if confirm=="YES":
    ### call the function here
    dedup_merged_collections()
else:
    print "nevermind, then."

