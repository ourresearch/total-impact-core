#!/usr/bin/env python
import argparse
import logging, os, sys, random, datetime, time
import requests
from sqlalchemy.sql import text    

from totalimpact import tiredis
from totalimpact import app, db
from totalimpact import item as item_module

logger = logging.getLogger('ti.updater')
logger.setLevel(logging.DEBUG)

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python totalimpact/updater.py


def update_by_tiids(all_tiids, number_to_update, myredis):
    tiids_to_update = all_tiids[0:min(number_to_update, len(all_tiids))]
    now = datetime.datetime.utcnow().isoformat()

    print "updating {number_to_update} of them now".format(number_to_update=number_to_update)
    QUEUE_DELAY_IN_SECONDS = 0.25
    for tiid in tiids_to_update:
        item_obj = item_module.Item.query.get(tiid)  # can use this method because don't need metrics
        item_doc = item_obj.as_old_doc()
        item_module.start_item_update(tiid, item_doc["aliases"], {}, "low", myredis)
        item_obj.last_update_run = now
        db.session.add(item_obj)
        time.sleep(QUEUE_DELAY_IN_SECONDS)
    db.session.commit()
    return tiids_to_update


# create table registered_tiid as (select tiid, api_key
# from alias, registered_item
# where alias.nid=registered_item.nid and alias.namespace=registered_item.namespace
# )

def get_tiids_not_updated_since(number_to_update, now=datetime.datetime.utcnow()):

    raw_sql = text("""SELECT tiid FROM item i
        WHERE last_update_run < now()::date - 7
        and tiid in 
        (select tiid
        from registered_tiid where api_key not in ('vanwijikc233acaa'))
        ORDER BY last_update_run DESC
        LIMIT :number_to_update""")

    result = db.session.execute(raw_sql, params={
        "number_to_update": number_to_update
        })
    tiids = [row["tiid"] for row in result]

    return tiids


def gold_update(number_to_update, myredis, now=datetime.datetime.utcnow()):
    tiids = get_tiids_not_updated_since(number_to_update, now)
    tiids_to_update = update_by_tiids(tiids, number_to_update, myredis)
    return tiids


def main(action_type, number_to_update=35, specific_publisher=None):
    #35 every 10 minutes is 35*6perhour*24hours=5040 per day

    redis_url = os.getenv("REDIS_URL")

    myredis = tiredis.from_url(redis_url)
    print "running " + action_type

    try:
        if action_type == "gold_update":
            tiids = gold_update(number_to_update, myredis)
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":

    # get args from the command line:
    parser = argparse.ArgumentParser(description="Run periodic metrics updating from the command line")
    parser.add_argument("action_type", type=str, help="The action to test; available actions are 'gold_update' (that's all right now)")
    parser.add_argument('--number_to_update', default='35', type=int, help="Number to update.")
    args = vars(parser.parse_args())
    print args
    print "updater.py starting."
    main(args["action_type"], args["number_to_update"])
