#!/usr/bin/env python
import argparse
import logging, os, sys, random, datetime, time, collections
import requests
from sqlalchemy.sql import text    

from totalimpact import tiredis
from totalimpact import app, db
from totalimpact import item as item_module

logger = logging.getLogger('ti.updater')
logger.setLevel(logging.DEBUG)

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python totalimpact/updater.py


def update_by_tiids(all_tiids, myredis):
    for tiid in all_tiids:
        item_obj = item_module.Item.query.get(tiid)  # can use this method because don't need metrics
        item_doc = item_obj.as_old_doc()
        item_module.start_item_update([{"tiid": item_doc["_id"], "aliases_dict":item_doc["aliases"]}], {}, "low", myredis)
    return all_tiids


def set_last_update_run(all_tiids):
    now = datetime.datetime.utcnow().isoformat()
    for tiid in all_tiids:
        item_obj = item_module.Item.query.get(tiid)  # can use this method because don't need metrics
        try:
            item_obj.last_update_run = now
            db.session.add(item_obj)
        except AttributeError:
            logger.warning(u"no object found for tiid {tiid} when updating last_update_run".format(
                tiid=tiid))

    db.session.commit()
    return all_tiids


# create table registered_tiid as (select tiid, api_key
# from alias, registered_item
# where alias.nid=registered_item.nid and alias.namespace=registered_item.namespace
# )

def get_registered_tiids_not_updated_since(number_to_update, now=datetime.datetime.utcnow()):

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

def get_nids_for_altmetric_com_to_update(number_to_update):

    raw_sql = text("""SELECT i.tiid, namespace, nid, last_update_run 
        FROM item i, alias a
        WHERE last_update_run < now()::date - 1
        AND i.tiid = a.tiid
        AND namespace in ('doi', 'arxiv', 'pmid')
        ORDER BY last_update_run DESC
        LIMIT :number_to_update""")

    result = db.session.execute(raw_sql, params={
        "number_to_update": number_to_update
        })
    #tiids = [row["tiid"] for row in result]

    return result.fetchall()


def get_altmetric_ids_from_nids(nids):
    nid_string = "|".join(nids)
    print "nid_string", nid_string

    headers = {u'content-type': u'application/x-www-form-urlencoded', 
                u'accept': u'application/json'}
    r = requests.post("http://api.altmetric.com/v1/translate?key=" + os.getenv("ALTMETRIC_COM_KEY"), 
                        data="ids="+nid_string, 
                        headers=headers)
    altmetric_ids_dict = r.json()

    nids_by_altmetric_id = dict((str(altmetric_ids_dict[nid]), nid) for nid in altmetric_ids_dict)
    return nids_by_altmetric_id


def altmetric_com_ids_to_update(altmetric_ids):
    altmetric_ids_string = ",".join(altmetric_ids)
    print "altmetric_ids_string", altmetric_ids_string

    headers = {u'content-type': u'application/x-www-form-urlencoded',
                u'accept': u'application/json'}

    r = requests.post("http://api.altmetric.com/v1/citations/1y?key=" + os.getenv("ALTMETRIC_COM_KEY"), 
                        data="citation_ids="+altmetric_ids_string, 
                        headers=headers)
    try:
        data = r.json()
        ids_with_changes = [str(entry["altmetric_id"]) for entry in data["results"]]    
    except:
        # says "Not Found" not in JSON if nothing found
        ids_with_changes = []
    return ids_with_changes


def tiids_from_altmetric_ids(altmetric_ids, nids_by_altmetric_id, tiids_by_nids):
    print "altmetric_ids", altmetric_ids
    nids = [nids_by_altmetric_id[id] for id in altmetric_ids]
    tiids_nested = [tiids_by_nids[nid] for nid in nids]
    print "tiids_nested", tiids_nested
    tiids = [tiid for inner_list in tiids_nested for tiid in inner_list]
    print "tiids", tiids
    return tiids


def altmetric_com_update(number_to_update, myredis):
    candidate_tiid_rows = get_nids_for_altmetric_com_to_update(number_to_update)
    tiids_by_nids = collections.defaultdict(list)
    for row in candidate_tiid_rows:
        tiids_by_nids[row["nid"]] += [row["tiid"]]
    print "tiids_by_nids", tiids_by_nids
    all_tiids = [row["tiid"] for row in candidate_tiid_rows]
    print "all_tiids", all_tiids

    nids = tiids_by_nids.keys()
    if not nids:
        logger.info("no items to update")
        return []
    print "nids", nids
    nids_by_altmetric_id = get_altmetric_ids_from_nids(nids)
    print "nids_by_altmetric_id", nids_by_altmetric_id

    altmetric_ids = nids_by_altmetric_id.keys()
    print "altmetric_ids", altmetric_ids

    if altmetric_ids:
        tiids_with_altmetric_ids = tiids_from_altmetric_ids(altmetric_ids, nids_by_altmetric_id, tiids_by_nids)
        updated_tiids = update_by_tiids(tiids_with_altmetric_ids, myredis)

        # altmetric_ids_with_changes = altmetric_com_ids_to_update(altmetric_ids, nids_by_altmetric_id, tiids_by_nids)
        # tiids_with_changes = tiids_from_altmetric_ids(altmetric_ids_with_changes)
        # updated_tiids = update_by_tiids(tiids_with_changes, myredis)

    else:
        tiids_with_changes = []

    if all_tiids:
        set_last_update_run(all_tiids)
    return tiids_with_changes


def gold_update(number_to_update, myredis, now=datetime.datetime.utcnow()):
    tiids = get_registered_tiids_not_updated_since(number_to_update, now)
    updated_tiids = update_by_tiids(tiids, myredis)
    return updated_tiids


def main(action_type, number_to_update=35, specific_publisher=None):
    #35 every 10 minutes is 35*6perhour*24hours=5040 per day

    redis_url = os.getenv("REDIS_URL")

    myredis = tiredis.from_url(redis_url)
    print u"running " + action_type

    try:
        if action_type == "gold_update":
            tiids = gold_update(number_to_update, myredis)
        elif action_type == "altmetric_com":
            tiids = altmetric_com_update(number_to_update, myredis)
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
