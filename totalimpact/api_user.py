import datetime
import shortuuid

import logging
logger = logging.getLogger('ti.api_user')

def make(prefix, **meta):
    api_user_doc = {}

    new_api_key = prefix.upper() + shortuuid.uuid().lower()[0:6]
    now = datetime.datetime.now().isoformat()

    api_user_doc["created"] = now
    api_user_doc["type"] = "api_user"
    api_user_doc["meta"] = meta
    api_user_doc["current_key"] = new_api_key
    api_user_doc["key_history"] = {now: new_api_key}
    api_user_doc["max_registered_items"] = 1000
    api_user_doc["registered_items"] = {}
    api_user_doc["_id"] = shortuuid.uuid()[0:24]

    return (api_user_doc, new_api_key)


def register_item(alias, tiid, api_key, mydao):
    api_user_id = get_api_user_id_by_api_key(api_key, mydao)

    api_user_doc = mydao.db.get(api_user_id)
    used_registration_spots = len(api_user_doc["registered_items"])
    remaining_registration_spots = api_user_doc["max_registered_items"] - used_registration_spots

    if remaining_registration_spots <= 0:
        return None

    # do the registering
    now = datetime.datetime.now().isoformat()

    api_user_doc["registered_items"][alias] = {
        "registered_date": now,
        "tiid": tiid
    }

    mydao.db.save(api_user_doc)
    used_registration_spots = len(api_user_doc["registered_items"])
    remaining_registration_spots = api_user_doc["max_registered_items"] - used_registration_spots

    return(remaining_registration_spots)


def get_api_user_id_by_api_key(api_key, mydao):
    logger.debug("In get_api_user_by_api_key with {api_key}".format(
        api_key=api_key))

    # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults# for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
    res = mydao.view('api_users_by_api_key/api_users_by_api_key')
    print res

    matches = res[[api_key]] 

    if matches.rows:
        api_user_id = matches.rows[0]["id"]
        logger.debug("found a match for {api_key}!".format(api_key=api_key))
        print matches.rows[0]
    else:
        api_user_id = None
        logger.debug("no match for api_key {api_key}!".format(api_key=api_key))
    return (api_user_id)


