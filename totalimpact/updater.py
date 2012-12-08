#!/usr/bin/env python

import logging, couchdb, os, sys
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
                    "issn": "0953-8585",
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

def update_dois(doi_prefix, myredis, mydao):
    dois = get_matching_dois_in_db(doi_prefix, mydao)
    aliases = [("doi", doi) for doi in dois]
    (tiids, new_items) = ItemFactory.create_or_find_items_from_aliases(aliases, myredis, mydao)
    print tiids
    QUEUE_DELAY_IN_SECONDS = 1.0
    ItemFactory.start_item_update(tiids, myredis, mydao, sleep_in_seconds=QUEUE_DELAY_IN_SECONDS)
    return tiids

def update_active_publisher_items(myredis, mydao):
    all_tiids = []
    for publisher in active_publishers:
        for journal_dict in active_publishers[publisher]["journals"]:
            tiids = update_dois(journal_dict["doi_prefix"], myredis, mydao)
            logger.info("sent update to {num_tiids} items for doi prefix {prefix}".format(
                num_tiids=len(tiids), prefix=journal_dict["doi_prefix"]))
            all_tiids += tiids
    return all_tiids

def main():
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")
    redis_url = os.getenv("REDISTOGO_URL")

    mydao = dao.Dao(cloudant_url, cloudant_db)
    myredis = tiredis.from_url(redis_url)

    try:
        tiids = update_active_publisher_items(myreds, mydao)
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
