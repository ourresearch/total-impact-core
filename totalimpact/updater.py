#!/usr/bin/env python
import argparse
import logging, os, sys, random, datetime, time
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
        item_module.start_item_update(tiid, item_doc["aliases"], myredis)
        item_obj.last_update_run = now
        db.session.add(item_obj)
        time.sleep(QUEUE_DELAY_IN_SECONDS)
    db.session.commit()
    return tiids_to_update


def get_tiids_not_updated_since(schedule, number_to_update, now=datetime.datetime.utcnow()):

    if schedule["exclude_old"]:
        raw_sql = text("""SELECT tiid FROM item i
                            WHERE created > now()::date - :max_days_since_created
                            AND last_update_run < now()::date - :max_days_since_updated
                            AND NOT EXISTS (select * from biblio where tiid = i.tiid and biblio_name='year' and replace(biblio_value, '"', '') < '2013')
                            ORDER BY last_update_run DESC
                            LIMIT :number_to_update""")
    else:
        raw_sql = text("""SELECT tiid FROM item i
                            WHERE created > now()::date - :max_days_since_created
                            AND last_update_run < now()::date - :max_days_since_updated
                            ORDER BY last_update_run DESC
                            LIMIT :number_to_update""")

    result = db.session.execute(raw_sql, params={
        "max_days_since_created": schedule["max_days_since_created"], 
        "max_days_since_updated": schedule["max_days_since_updated"], 
        "number_to_update": number_to_update
        })
    tiids = [row["tiid"] for row in result]

    return tiids

gold_update_schedule = [
    {"group":"A", "max_days_since_created": 7, "max_days_since_updated": 1, "exclude_old": True},
    {"group":"B", "max_days_since_created": 30, "max_days_since_updated": 7 , "exclude_old": True},
    {"group":"C", "max_days_since_created": 365*100, "max_days_since_updated": 30, "exclude_old": False}] #everything else once a month

def gold_update(number_to_update, myredis, now=datetime.datetime.now()):
    all_tiids = []
    tiids_to_update = []
    # do magic
    for schedule in gold_update_schedule:
        if (len(all_tiids) < number_to_update):
            number_still_avail = number_to_update-len(all_tiids)
            tiids = get_tiids_not_updated_since(schedule, number_still_avail, now)
            print "got", len(tiids), "for update schedule", schedule
            all_tiids += tiids
            if tiids:
                print tiids
                tiids_to_update = update_by_tiids(tiids, number_still_avail, myredis)
    return all_tiids

def main(action_type, number_to_update=35, specific_publisher=None):
    #35 every 10 minutes is 35*6perhour*24hours=5040 per day

    redis_url = os.getenv("REDIS_URL")

    myredis = tiredis.from_url(redis_url)

    try:
        if action_type == "gold_update":
            print "running " + action_type
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
