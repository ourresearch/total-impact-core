#!/usr/bin/env python

import logging, couchdb, os, sys
from totalimpact import dao, tiredis
from totalimpact.models import ItemFactory

logger = logging.getLogger('ti.updater')
logger.setLevel(logging.DEBUG)

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python totalimpact/updater.py


def get_elife_dois(mydao):
    db = mydao.db
    dois = []
    view_name = "queues/by_alias"
    view_rows = db.view(view_name, 
            include_docs=False, 
            startkey=["doi", "10.7554/eLife.0000000000"], 
            endkey=["doi", "10.7554/eLife.zzzzzzzzzz"])
    row_count = 0

    for row in view_rows:
        row_count += 1
        doi = row.key[1]
        if doi not in dois:
            dois += [doi]
        #logger.info("\n%s" % (doi))
    return dois

def update_elife_dois(myredis, mydao):
    dois = get_elife_dois(mydao)
    aliases = [("doi", doi) for doi in dois]
    (tiids, new_items) = ItemFactory.create_or_find_items_from_aliases(aliases, myredis, mydao)
    QUEUE_DELAY_IN_SECONDS = 1.0
    ItemFactory.start_item_update(tiids, myredis, mydao, sleep_in_seconds=QUEUE_DELAY_IN_SECONDS)
    return tiids

def main():
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")
    redis_url = os.getenv("REDISTOGO_URL")

    mydao = dao.Dao(cloudant_url, cloudant_db)
    myredis = tiredis.from_url(redis_url)

    try:
        tiids = update_elife_dois(myredis, mydao)
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
