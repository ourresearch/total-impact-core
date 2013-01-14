#!/usr/bin/env python
import argparse
import logging, couchdb, os, sys, random, datetime

from totalimpact import dao, tiredis, item, mixpanel

logger = logging.getLogger('ti.updater')
logger.setLevel(logging.DEBUG)

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python totalimpact/updater.py

active_publishers = {
    "elife": {
        "api_key": "",
        "journals": [
                { 
                    "title": "eLife",
                    "issn": "2050-084X",
                    "doi_prefix": "10.7554/eLife"
                }
            ]
        },
    "pensoft": {
        "api_key": "",
        "journals": [
                {  
                    "title": "ZooKeys",
                    "issn": "1313-2970",
                    "doi_prefix": "10.3897/zookeys"
                },
                {  
                    "title": "PhytoKeys",
                    "issn": "1314-2003",
                    "doi_prefix": "10.3897/phytokeys"
                },
                {  
                    "title": "BioRisk",
                    "issn": "1313-2652",
                    "doi_prefix": "10.3897/biorisk"
                },
                {  
                    "title": "NeoBiota",
                    "issn": "1314-2488",
                    "doi_prefix": "10.3897/neobiota"
                },
                {  
                    "title": "Journal of Hymenoptera Research",
                    "issn": "1314-2607",
                    "doi_prefix": " 10.3897/JHR"
                }
            ]
        },
    "ubiquity_press": {
        "api_key": "",
        "journals": [
                {  
                    "title": "Archaeology International",
                    "issn": "2048-4194",
                    "doi_prefix": "10.5334/ai"
                },
                {  
                    "title": "The Bulletin of the History of Archaeology",
                    "issn": "2047-6930",
                    "doi_prefix": "10.5334/bha"
                },
                {  
                    "title": "Stability: International Journal of Security and Development",
                    "issn": "2165-2627",
                    "doi_prefix": "10.5334/sta"
                },
                {  
                    "title": "Journal of Conservation and Museum Studies",
                    "issn": "1364-0429",
                    "doi_prefix": "10.5334/jcms"
                },
                {  
                    "title": "Journal of Open Archaeology Data",
                    "issn": "2049-1565",
                    "doi_prefix": "10.5334/data"  # but also some without a prefix
                },
                {  
                    "title": "Opticon1826",
                    "issn": "2049-8128",
                    "doi_prefix": "10.5334/opt"
                },
                {  
                    "title": "Papers from the Institute of Archaeology",
                    "issn": "2041-9015",
                    "doi_prefix": "10.5334/pia"
                },
                {  
                    "title": "Present Pasts",
                    "issn": "1759-2941",
                    "doi_prefix": "10.5334/pp"
                },

            ]
        }        
    }


def get_matching_dois_in_db(min_year, doi_prefix, mydao):
    db = mydao.db
    dois_to_update = []
    docs_to_update = []
    tiids_to_update = []

    view_name = "doi_prefixes_by_last_update_run/doi_prefixes_by_last_update_run"
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)

    # get items updated more than 24 hours ago
    view_rows = db.view(view_name, 
            include_docs=True, 
            startkey=[doi_prefix.lower(), "00000000"], 
            endkey=[doi_prefix.lower(), yesterday.isoformat()])
    for row in view_rows:
        doc = row.doc
        tiid = doc["_id"]
        #only update items published since the a given year
        try:
            year = doc["biblio"]["year"]
        except KeyError:
            continue
        if year > min_year:
            if tiid not in tiids_to_update:
                docs_to_update += [doc]
                tiids_to_update += [tiid]
    return (tiids_to_update, docs_to_update)

def get_least_recently_updated_items_from_doi_prefix(min_year, doi_prefix, myredis, mydao):
    (tiids_to_update, docs_to_update) = get_matching_dois_in_db(min_year, doi_prefix, mydao)
    return (tiids_to_update, docs_to_update)

def update_active_publisher_items(number_to_update, myredis, mydao):
    all_tiids = []
    all_docs = []
    for publisher in active_publishers:
        for journal_dict in active_publishers[publisher]["journals"]:
            min_year = 2011  #only update 2012-2013 right now
            (tiids_from_doi_prefix, docs_from_doi_prefix) = get_least_recently_updated_items_from_doi_prefix(min_year, journal_dict["doi_prefix"], myredis, mydao)
            logger.info("doi prefix {prefix} has {num_tiids} items published since {min_year} last updated more than 24 hours ago".format(
                num_tiids=len(tiids_from_doi_prefix), prefix=journal_dict["doi_prefix"], min_year=min_year))
            all_tiids += tiids_from_doi_prefix
            all_docs += docs_from_doi_prefix

    print "recent items for active publishers that were last updated more than a day ago, n=", len(all_tiids)
    tiids_to_update = all_tiids[0:min(number_to_update, len(all_tiids))]
    docs_to_update = all_docs[0:min(number_to_update, len(all_docs))]
    response = update_docs_with_updater_timestamp(docs_to_update, mydao)        

    print "updating {number_to_update} of them now".format(number_to_update=number_to_update)
    QUEUE_DELAY_IN_SECONDS = 0.25
    mixpanel.track("Trigger:Update", {"Number Items":len(tiids_to_update), "Update Type":"Scheduled Registered"})
    item.start_item_update(tiids_to_update, myredis, mydao, sleep_in_seconds=QUEUE_DELAY_IN_SECONDS)

    return tiids_to_update

def get_least_recently_updated_tiids_in_db(number_to_update, mydao):
    db = mydao.db
    tiids = []
    view_name = "update/items_by_last_update_run"
    view_rows = db.view(view_name, 
            include_docs=True, 
            descending=False, 
            limit=number_to_update)
    tiids = [row.id for row in view_rows]
    docs = [row.doc for row in view_rows]
    return (tiids, docs)

def update_docs_with_updater_timestamp(docs, mydao):
    db = mydao.db
    now = datetime.datetime.now().isoformat()
    for doc in docs:
        doc["last_update_run"] = now
    update_response = db.update(docs)
    print update_response
    return update_response
    
def update_least_recently_updated(number_to_update, myredis, mydao):
    (tiids_to_update, docs) = get_least_recently_updated_tiids_in_db(number_to_update, mydao)
    update_docs_with_updater_timestamp(docs, mydao)
    QUEUE_DELAY_IN_SECONDS = 0.25
    mixpanel.track("Trigger:Update", {"Number Items":len(tiids_to_update), "Update Type":"Scheduled Least Recently"})
    item.start_item_update(tiids_to_update, myredis, mydao, sleep_in_seconds=QUEUE_DELAY_IN_SECONDS)
    return tiids_to_update

def main(action_type, number_to_update=35):
    #35 every 10 minutes is 35*6perhour*24hours=5040 per day

    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")
    redis_url = os.getenv("REDIS_URL")

    mydao = dao.Dao(cloudant_url, cloudant_db)
    myredis = tiredis.from_url(redis_url)

    try:
        if action_type == "active_publishers":
            print "running " + action_type
            tiids = update_active_publisher_items(number_to_update, myredis, mydao)
        elif action_type == "least_recently_updated":
            print "running " + action_type
            tiids = update_least_recently_updated(number_to_update, myredis, mydao)
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    # get args from the command line:
    parser = argparse.ArgumentParser(description="Run periodic metrics updating from the command line")
    parser.add_argument("action_type", type=str, help="The action to test; available actions are 'active_publishers' and 'least_recently_updated'")
    parser.add_argument('--number_to_update', default='35', type=int, help="Number to update.")
    args = vars(parser.parse_args())
    print args
    print "updater.py starting."
    main(args["action_type"], args["number_to_update"])
