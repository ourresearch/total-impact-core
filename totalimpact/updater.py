#!/usr/bin/env python
import argparse
import logging, couchdb, os, sys, random
from totalimpact import dao, tiredis
from totalimpact.models import ItemFactory

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
                    "doi_prefix": "10.7554/eLife."
                }
            ]
        },
    "pensoft": {
        "api_key": "",
        "journals": [
                {  
                    "title": "ZooKeys",
                    "issn": "1313-2970",
                    "doi_prefix": "10.3897/zookeys."
                },
                {  
                    "title": "PhytoKeys",
                    "issn": "1314-2003",
                    "doi_prefix": "10.3897/phytokeys."
                },
                {  
                    "title": "BioRisk",
                    "issn": "1313-2652",
                    "doi_prefix": "10.3897/biorisk."
                },
                {  
                    "title": "NeoBiota",
                    "issn": "1314-2488",
                    "doi_prefix": "10.3897/neobiota."
                },
                {  
                    "title": "Journal of Hymenoptera Research",
                    "issn": "1314-2607",
                    "doi_prefix": " 10.3897/JHR."
                }
            ]
        },
    "ubiquity_press": {
        "api_key": "",
        "journals": [
                {  
                    "title": "Archaeology International",
                    "issn": "2048-4194",
                    "doi_prefix": "10.5334/ai."
                },
                {  
                    "title": "The Bulletin of the History of Archaeology",
                    "issn": "2047-6930",
                    "doi_prefix": "10.5334/bha."
                },
                {  
                    "title": "Stability: International Journal of Security and Development",
                    "issn": "2165-2627",
                    "doi_prefix": "10.5334/sta."
                },
                {  
                    "title": "Journal of Conservation and Museum Studies",
                    "issn": "1364-0429",
                    "doi_prefix": "10.5334/jcms."
                },
                {  
                    "title": "Journal of Open Archaeology Data",
                    "issn": "2049-1565",
                    "doi_prefix": "10.5334/data."  # but also some without a prefix
                },
                {  
                    "title": "Opticon1826",
                    "issn": "2049-8128",
                    "doi_prefix": "10.5334/opt."
                },
                {  
                    "title": "Papers from the Institute of Archaeology",
                    "issn": "2041-9015",
                    "doi_prefix": "10.5334/pia."
                },
                {  
                    "title": "Present Pasts",
                    "issn": "1759-2941",
                    "doi_prefix": "10.5334/pp."
                },

            ]
        }        
    }


def get_matching_dois_in_db(doi_prefix, mydao):
    db = mydao.db
    dois = []
    view_name = "queues/by_alias"
    view_rows = db.view(view_name, 
            include_docs=False, 
            startkey=["doi", doi_prefix.lower() + "00000000000"], 
            endkey=["doi", doi_prefix.lower() + "zzzzzzzzzzzz"])
    row_count = 0

    for row in view_rows:
        row_count += 1
        doi = row.key[1]
        if doi not in dois:
            dois += [doi]
        #logger.info("\n%s" % (doi))
    return dois

def update_dois_from_doi_prefix(doi_prefix, myredis, mydao):
    dois = get_matching_dois_in_db(doi_prefix, mydao)
    aliases = [("doi", doi) for doi in dois]
    (old_and_new_tiids, new_items) = ItemFactory.create_or_find_items_from_aliases(aliases, myredis, mydao)
    print old_and_new_tiids
    number_to_sample = min(200, len(old_and_new_tiids))
    tiids_to_update = random.sample(old_and_new_tiids, number_to_sample)
    QUEUE_DELAY_IN_SECONDS = 1.0
    ItemFactory.start_item_update(tiids_to_update, myredis, mydao, sleep_in_seconds=QUEUE_DELAY_IN_SECONDS)
    return tiids_to_update

def update_active_publisher_items(myredis, mydao):
    all_tiids = []
    for publisher in active_publishers:
        for journal_dict in active_publishers[publisher]["journals"]:
            tiids = update_dois_from_doi_prefix(journal_dict["doi_prefix"], myredis, mydao)
            logger.info("sent update to {num_tiids} items for doi prefix {prefix}".format(
                num_tiids=len(tiids), prefix=journal_dict["doi_prefix"]))
            all_tiids += tiids
    return all_tiids

def get_least_recently_updated_tiids_in_db(number_to_update, mydao):
    db = mydao.db
    tiids = []
    view_name = "update/items_by_last_modified"
    view_rows = db.view(view_name, 
            include_docs=False, 
            descending=True, 
            limit=number_to_update)
    tiids = [row.key[1] for row in view_rows]
    return tiids

def update_least_recently_modified(number_to_update, myredis, mydao):
    tiids_to_update = get_least_recently_updated_tiids_in_db(number_to_update, mydao)
    QUEUE_DELAY_IN_SECONDS = 1.0
    ItemFactory.start_item_update(tiids_to_update, myredis, mydao, sleep_in_seconds=QUEUE_DELAY_IN_SECONDS)
    return tiids_to_update

def main(run_publisher=False, run_least_recently_modified=True):
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")
    redis_url = os.getenv("REDISTOGO_URL")

    mydao = dao.Dao(cloudant_url, cloudant_db)
    myredis = tiredis.from_url(redis_url)

    number_to_update = 35  #35 every 10 minutes is 35*6perhour*24hours=5040 per day

    try:
        if run_publisher:
            tiids = update_active_publisher_items(myredis, mydao)
        if run_least_recently_modified:
            tiids = update_least_recently_modified(number_to_update, myredis, mydao)
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    # get args from the command line:
    parser = argparse.ArgumentParser(description="Run periodic metrics updating from the command line")
    #parser.add_argument("action_type", type=str, help="The action to test; available actions listed in fakes.py")
    args = vars(parser.parse_args())
    print args
    print "updater.py starting."
    run_publisher = False
    run_least_recently_modified = True

    main(run_publisher, run_least_recently_modified)
