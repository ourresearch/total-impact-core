import couchdb, os, logging, sys, collections
from pprint import pprint
import time
import requests
import copy

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/db_housekeeping/merge_collections.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("merge_collections")
 
cloudant_db = os.getenv("CLOUDANT_DB")
cloudant_url = os.getenv("CLOUDANT_URL")

couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

def make_similar_collection(base_doc, alias_tiid_tuples):
    collection_doc = {}
    for key in ["type", "owner", "last_modified", "ip_address", "key_hash", "created"]:
        try:
            collection_doc[key] = base_doc[key]
        except KeyError:
            pass  #some collections don't have key_hash it looks like

    collection_doc["_id"] = "00" + base_doc["_id"][2:]
    collection_doc["title"] = "all my products"
    collection_doc["alias_tiids"] = {} 
    for (alias, tiid) in alias_tiid_tuples:
        collection_doc["alias_tiids"][alias] = tiid
    return collection_doc

def merge_collections_for_profile():
    from totalimpact import item, tiredis

    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, include_docs=True)
    row_count = 0
    page_size = 500
    start_key = ["user", "00000000000"]
    end_key = ["user", "zzzzzzzzz"]

    from couch_paginator import CouchPaginator
    page = CouchPaginator(db, view_name, page_size, include_docs=True, start_key=start_key, end_key=end_key)

    while page:
        for row in page:
            row_count += 1
            user_doc = row.doc

            if "profile_collection" in user_doc:
                #already updated
                if not user_doc["colls"]:
                    user_doc["profile_collection"] = None
                    print "updating profile_collection with None because no collections", row.id
                    db.save(user_doc)
                continue 

            alias_tiid_tuples = []

            print "\nstill needs a profile_collection:", row.id, 
            print user_doc

            try:
                my_collections = user_doc["colls"]
                for coll in my_collections:
                    collection_doc = db.get(coll)
                    alias_tiids = collection_doc["alias_tiids"]
                    alias_tiid_tuples += alias_tiids.items()

                profile_collection = None    
                if (len(my_collections) == 1):
                    profile_collection = collection_doc["_id"]
                    print "only one collection so merged collection not needed"
                elif (len(my_collections) > 1):
                    merged_collection = make_similar_collection(collection_doc, alias_tiid_tuples)
                    
                    #save new collection
                    del collection_doc["_rev"]
                    try:
                        db.save(merged_collection)
                        print "saved merged collection", merged_collection["_id"]
                    except couchdb.http.ResourceConflict:
                        print "didn't save new merged collection because of document conflict... maybe already saved"

                    profile_collection = merged_collection["_id"]

                print profile_collection
                user_doc["profile_collection"] = profile_collection
                db.save(user_doc)
                print "saved user_doc with updated profile collection"
            except KeyError:
                raise
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
    merge_collections_for_profile()
else:
    print "nevermind, then."

