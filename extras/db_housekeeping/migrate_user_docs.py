import couchdb, os, logging, sys, collections
from pprint import pprint
import time
import requests
import copy
import random
import datetime
from werkzeug.security import generate_password_hash

from totalimpact import dao
import psycopg2

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/db_housekeeping/migrate_user_docs.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("merge_collections")
 
# set up couchdb
cloudant_db = os.getenv("CLOUDANT_DB")
cloudant_url = os.getenv("CLOUDANT_URL")
couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

# set up postgres
mypostgresdao = dao.PostgresDao(os.environ["POSTGRESQL_URL"])
cur = mypostgresdao.get_cursor()
logger.info("connected to postgres")


default_password = "welcome"
default_password_hash = generate_password_hash(default_password)

def insert_unless_error(select_statement, save_list):
    #print "try to insert"
    #cur.executemany(select_statement, save_list)
    for l in save_list:
        print cur.mogrify(select_statement, l)
        try:
            #cur.execute(select_statement, l)
            pass
        except psycopg2.IntegrityError:
            print "insert already exists"

def insert_string(tablename, colnames):
    colnames_string = ", ".join(colnames)
    percent_colnames_string = ", ".join(["%("+col+")s" for col in colnames])
    insert = "INSERT INTO {tablename} ({colnames_string}) VALUES ({percent_colnames_string});\t".format(
        tablename=tablename, 
        colnames_string=colnames_string, 
        percent_colnames_string=percent_colnames_string)
    return insert


def merge_collections_for_profile():
    from totalimpact import item, tiredis

    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, include_docs=True)
    row_count = 0
    sql_statement_count = 0
    page_size = 500
    start_key = ["user", "00000000000"]
    end_key = ["user", "zzzzzzzzz"]

    from couch_paginator import CouchPaginator
    page = CouchPaginator(db, view_name, page_size, include_docs=True, start_key=start_key, end_key=end_key)

    email_data_strings = []

    while page:
        for row in page:

            row_count += 1
            user_doc = row.doc

            rowdata = {}
            rowdata["email"] = user_doc["_id"]
            if not user_doc["profile_collection"]:
                #print "not migrating this doc because it has no collections"
                continue
            rowdata["collection_id"] = user_doc["profile_collection"]
            try:
                rowdata["created"] = user_doc["created"]
            except KeyError:
                rowdata["created"] = datetime.datetime(2013, 1, 1).isoformat()                
            rowdata["password_hash"] = default_password_hash
            rowdata["url_slug"] = "user" + str(50000 + row_count)
            rowdata["given_name"] = "Firstname"
            rowdata["surname"] = "Lastname"

            insert_unless_error(insert_string('"user"', rowdata.keys()), [rowdata])
            sql_statement_count += 1

            # pull information together to send out surveymonkey email
            profile_id = user_doc["profile_collection"]
            email = user_doc["_id"]
            profile_doc = db.get(profile_id)
            my_collections = user_doc["colls"]

            title = profile_doc["title"]
            if (len(my_collections) > 1):
                title = ""
                for cid in my_collections:
                    coll_doc = db.get(cid)
                    collection_title = coll_doc["title"]
                    if collection_title != "My Collection":
                        title += "*" + collection_title

            try:
                collections_string = str(";".join(my_collections.keys()))
            except UnicodeEncodeError:
                print "UnicodeEncodeError on ", email, "so setting collections to blank"
                collections_string = ""

            email_data_strings += [u"{url_slug}|{profile_id}|{len_profile}|{email}|{created}|{title}|{collections_string}".format(
                url_slug=rowdata["url_slug"],
                profile_id=profile_id,
                email=email,
                len_profile=len(profile_doc["alias_tiids"]),
                created=rowdata["created"],
                title=title,
                collections_string=collections_string)]

        logger.info("%i. getting new page, last id was %s" %(row_count, row.id))
        if page.has_next:
            page = CouchPaginator(db, view_name, page_size, start_key=page.next, end_key=end_key, include_docs=True)
        else:
            page = None

    print "Number of rows: ", row_count
    print "Number of sql statements: ", sql_statement_count

    print "\n\n\n"
    for line in email_data_strings:
        print line

if (cloudant_db == "ti"):
    print "\n\nTHIS MAY BE THE PRODUCTION DATABASE!!!"
else:
    print "\n\nThis doesn't appear to be the production database"

# remove check so can pipe output to a file: this script does not change the db so it is safe!
# confirm = None
# confirm = raw_input("\nType YES if you are sure you want to run this test:")
##if confirm=="YES":
    ### call the function here
merge_collections_for_profile()
#else:
#    print "nevermind, then."

