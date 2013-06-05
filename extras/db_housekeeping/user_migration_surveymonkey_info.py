import couchdb, os, logging, sys, collections
from pprint import pprint
import time
import requests
import copy

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/db_housekeeping/user_migration_surveymonkey_info.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("user_migration_surveymonkey_info")
 
cloudant_db = os.getenv("CLOUDANT_DB")
cloudant_url = os.getenv("CLOUDANT_URL")

couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

def user_migration_surveymonkey_info():
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

            if not "profile_collection" in user_doc:
                continue

            try:
                profile_id = user_doc["profile_collection"]
                if not profile_id:
                    continue
                email = user_doc["_id"]
                profile_doc = db.get(profile_id)
                my_collections = user_doc["colls"]

                print "{profile_id},{len_profile},{email},{collections_string}".format(
                    profile_id=profile_id,
                    email=email,
                    len_profile=len(profile_doc["alias_tiids"]),
                    collections_string=";".join(my_collections.keys()))

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
    user_migration_surveymonkey_info()
else:
    print "nevermind, then."

