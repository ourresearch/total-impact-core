import couchdb, os, logging, sys, collections
from pprint import pprint
import time, datetime, json
import requests

from couch_paginator import CouchPaginator
from totalimpact import dao
import psycopg2

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/db_housekeeping/postgres_mirror.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("postgres_mirror")
 


def action_on_a_page_single_doc(page):
    docs = [row.doc for row in page]
    for doc in docs:
        doc["tiid"] = doc["_id"]
        try:
            doc["last_update_run"]
        except KeyError:
            doc["last_update_run"] = None        

        print "try"
        try:
            print doc["tiid"]
            cur.execute("""INSERT INTO items(tiid, created, last_modified, last_update_run) 
                            VALUES (%(tiid)s, %(created)s, %(last_modified)s, %(last_update_run)s)""", doc)
            #conn.commit()
        except psycopg2.IntegrityError:
            print "row already exists"
            mypostgresdao.conn.rollback()
        except:
            mypostgresdao.conn.rollback()
        finally:
            pass

def build_items_save_list(items):
    items_save_list = []
    for item in items:
        item["tiid"] = item["_id"]
        try:
            item["last_update_run"]
        except KeyError:
            item["last_update_run"] = None 
        items_save_list += [item]
    return items_save_list  

def build_metrics_save_list(items):
    metrics_save_list = []
    for item in items:
        if "metrics" in item:
            for full_metric_name in item["metrics"]:
                for timestamp in item["metrics"][full_metric_name]["values"]["raw_history"]:
                    (provider, bare_metric_name) = full_metric_name.split(":")
                    metrics_save_list += [{"tiid":item["_id"],
                                "provider":provider,
                                "metric_name":bare_metric_name,
                                "collected_date":timestamp,
                                "drilldown_url":item["metrics"][full_metric_name]["provenance_url"],
                                "raw_value":item["metrics"][full_metric_name]["values"]["raw_history"][timestamp]
                                }]
    return metrics_save_list

def build_aliases_save_list(items):
    aliases_save_list = []
    for item in items:
        if "aliases" in item:
            for namespace in item["aliases"]:
                for nid in item["aliases"][namespace]:
                    aliases_save_list += [{"tiid":item["_id"],
                                "provider":"unknown",
                                "namespace":namespace,
                                "nid":nid,
                                "collected_date":now
                                }]
    return aliases_save_list

class NoneDict(dict):
    # returns None if key not defined instead of throwing KeyError
    def __getitem__(self, key):
        return dict.get(self, key)

def build_biblio_save_list(items):
    biblio_save_list = []
    for item in items:
        if "biblio" in item:
            biblio_save = NoneDict()
            biblio_save.update(item["biblio"])

            biblio_save["tiid"] = item["_id"]
            biblio_save["collected_date"] = now

            biblio_save["authors_lnames"] = None

            if "owner" in biblio_save:
                biblio_save["provider"] = "github"
                biblio_save["host"] = "github"
            else:
                biblio_save["provider"] = "unknown"

            if "year" in biblio_save:
                biblio_save["year_published"] = int(biblio_save["year"])
            if "owner" in biblio_save:
                biblio_save["authors_raw"] = biblio_save["owner"]
            if "create_date" in biblio_save:
                biblio_save["date_published"] = biblio_save["create_date"]
            if "journal" in biblio_save:
                biblio_save["host"] = biblio_save["journal"]

            biblio_save_list += [biblio_save]

    return biblio_save_list    

"""
CREATE TABLE items (
    tiid text NOT NULL,
    created timestamptz,
    last_modified timestamptz,
    last_update_run timestamptz,
    PRIMARY KEY (tiid)
);

CREATE TABLE metrics (
    tiid text NOT NULL,
    provider text NOT NULL,
    metric_name text NOT NULL,
    collected_date timestamptz NOT NULL,
    drilldown_url text,
    raw_value text,
    PRIMARY KEY (tiid,provider,metric_name,collected_date)
);

CREATE TABLE aliases (
    tiid text NOT NULL,
    "namespace" text NOT NULL,
    nid text NOT NULL,
    last_modified timestamptz,
    PRIMARY KEY (tiid, "namespace", nid))

CREATE TABLE biblio (
    tiid text NOT NULL,
    provider text NOT NULL,
    last_modified timestamptz,
    title text,
    year_published numeric(25),
    date_published timestamptz,
    authors_lnames text,
    authors_raw text,
    "host" text,
    url text,
    description text,
    PRIMARY KEY (tiid, provider))

CREATE TABLE email (
    id text NOT NULL,
    created timestamptz,
    payload text NOT NULL,
    PRIMARY KEY (id))

"""

def insert_unless_error(select_statement, save_list):
    print "try to insert"
    #cur.executemany(select_statement, save_list)
    for l in save_list:
        print cur.mogrify(select_statement, l)
        try:
            #cur.execute(select_statement, l)
            pass
        except psycopg2.IntegrityError:
            print "insert already exists"

def item_action_on_a_page(page):
    items = [row.doc for row in page]

    print "ITEMS"
    print datetime.datetime.now().isoformat()
    items_save_list = build_items_save_list(items)
    print datetime.datetime.now().isoformat()
    insert_unless_error("""INSERT INTO items(tiid, created, last_modified, last_update_run) 
                        VALUES (%(tiid)s, %(created)s, %(last_modified)s, %(last_update_run)s);""", 
                        items_save_list)

    print "BIBLIO"
    print datetime.datetime.now().isoformat()
    biblio_save_list = build_biblio_save_list(items)
    print datetime.datetime.now().isoformat()
    insert_unless_error("""INSERT INTO biblio(tiid, provider, collected_date, title, year_published, date_published, authors_lnames, authors_raw, host, url, description) 
                        VALUES (%(tiid)s, %(provider)s, %(collected_date)s, %(title)s, %(year_published)s, %(date_published)s, %(authors_lnames)s, %(authors_raw)s, %(host)s, %(url)s, %(description)s)""", 
                        biblio_save_list)

    print "ALIASES"
    print datetime.datetime.now().isoformat()
    aliases_save_list = build_aliases_save_list(items)
    print datetime.datetime.now().isoformat()
    insert_unless_error("""INSERT INTO aliases(tiid, namespace, nid, collected_date) 
                        VALUES (%(tiid)s, %(namespace)s, %(nid)s, %(collected_date)s)""", 
                        aliases_save_list)

    print "METRICS"
    print datetime.datetime.now().isoformat()
    metrics_save_list = build_metrics_save_list(items)
    print datetime.datetime.now().isoformat()
    insert_unless_error("""INSERT INTO metrics(tiid, provider, metric_name, collected_date, drilldown_url, raw_value) 
                        VALUES (%(tiid)s, %(provider)s, %(metric_name)s, %(collected_date)s, %(drilldown_url)s, %(raw_value)s)""", 
                        metrics_save_list)


    print "done"

def build_email_save_list(emails):
    email_save_list = []
    for email in emails:
        print email["_id"]
        email_save = {}
        email_save["id"] = email["_id"]
        email_save["created"] = email["created"]
        email_save["payload"] = json.dumps(email["payload"])
        email_save_list += [email_save]
    return email_save_list  

def email_action_on_a_page(page):
    emails = [row.doc for row in page]
    print "EMAILS"
    print datetime.datetime.now().isoformat()
    emails_save_list = build_email_save_list(emails)
    print datetime.datetime.now().isoformat()
    insert_unless_error("""INSERT INTO email(id, created, payload) 
                    VALUES (%(id)s, %(created)s, %(payload)s);""", 
                    emails_save_list)
    print datetime.datetime.now().isoformat()
    print "done"


def build_api_users_save_list(docs):
    api_users_save_list = []
    registered_items_save_list = []
    for doc in docs:
        print doc["_id"]
        api_users_save = {}
        api_users_save["api_key"] = doc["current_key"]
        api_users_save["max_registered_items"] = doc["max_registered_items"]
        api_users_save["created"] = doc["created"]
        for key in doc["meta"]:
            api_users_save[key] = doc["meta"][key]
        api_users_save_list += [api_users_save]
        for alias in doc["registered_items"]:
            registered_items_save_list += [{
                "api_key":api_users_save["api_key"], 
                "registered_date":doc["registered_items"][alias]["registered_date"],
                "alias":alias}]    
    return (api_users_save_list, registered_items_save_list)  

def insert_string(tablename, colnames):
    colnames_string = ", ".join(colnames)
    percent_colnames_string = ", ".join(["%("+col+")s" for col in colnames])
    insert = "INSERT INTO {tablename} ({colnames_string}) VALUES ({percent_colnames_string});\t".format(
        tablename=tablename, 
        colnames_string=colnames_string, 
        percent_colnames_string=percent_colnames_string)
    return insert

def api_users_action_on_a_page(page):
    docs = [row.doc for row in page]
    print "API USERS"
    print datetime.datetime.now().isoformat()
    (api_users_save_list, registerted_items_save_list) = build_api_users_save_list(docs)
    print datetime.datetime.now().isoformat()

    colnames = "api_key, max_registered_items, created, planned_use, example_url, api_key_owner, notes, email, organization".split(", ")
    insert_unless_error(insert_string("api_users", colnames), api_users_save_list)

    colnames = "api_key, alias, registered_date".split(", ")
    insert_unless_error(insert_string("registered_items", colnames), registerted_items_save_list)

    print datetime.datetime.now().isoformat()
    print "done"


def run_on_documents(func_page, view_name, start_key, end_key, row_count=0, page_size=500):
    couch_page = CouchPaginator(db, view_name, page_size, start_key=start_key, end_key=end_key, include_docs=True)

    while couch_page:
        func_page(couch_page)
        row_count += page_size

        logger.info("%i. getting new page" %(row_count))
        if couch_page.has_next:
            couch_page = CouchPaginator(db, view_name, page_size, start_key=couch_page.next, end_key=end_key, include_docs=True)
        else:
            couch_page = None

    print "number items = ", row_count


#run


# set up postgres
mypostgresdao = dao.PostgresDao(os.environ["POSTGRESQL_URL"])
cur = mypostgresdao.get_cursor()
logger.info("connected to postgres")

# set up couchdb
cloudant_db = os.getenv("CLOUDANT_DB")
cloudant_url = os.getenv("CLOUDANT_URL")
couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
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

# set up the action code
#myview_name = "queues/by_alias"
#mystart_key = ["url", "https://github.0000000"]
#myend_key = ["url", "https://github.zzzzzzzz"]

myview_name = "by_type/by_type"
mystart_key = ["api_user"]
myend_key = ["api_user"]

now = datetime.datetime.now().isoformat()

run_on_documents(api_users_action_on_a_page, 
    view_name=myview_name, 
    start_key=mystart_key, 
    end_key=myend_key, 
    page_size=500)

cur.close()
mypostgresdao.close()

#    try:
#        cur.execute("CREATE TABLE phonebook(phone VARCHAR(32), firstname VARCHAR(32), lastname VARCHAR(32), address VARCHAR(64));")
#    except psycopg2.ProgrammingError:
#        print "table already exists"

#    cur.execute("SELECT * FROM phonebook ORDER BY lastname;")
#    print cur.fetchone()    

