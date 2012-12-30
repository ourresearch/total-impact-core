import datetime
import shortuuid

import logging
logger = logging.getLogger('ti.api_user')

def build_api_user(prefix, max_registered_items, **meta):
    api_user_doc = {}

    new_api_key = prefix.lower() + "-" + shortuuid.uuid().lower()[0:6]
    now = datetime.datetime.now().isoformat()

    api_user_doc["max_registered_items"] = int(max_registered_items)
    api_user_doc["created"] = now
    api_user_doc["type"] = "api_user"
    api_user_doc["meta"] = meta
    api_user_doc["current_key"] = new_api_key
    api_user_doc["key_history"] = {now: new_api_key}
    api_user_doc["registered_items"] = {}
    api_user_doc["_id"] = shortuuid.uuid()[0:24]

    return (api_user_doc, new_api_key)

class ApiLimitExceededException(Exception):
    pass

class InvalidApiKeyException(Exception):
    pass

def register_item(alias, tiid, api_key, mydao):
    api_user_id = get_api_user_id_by_api_key(api_key, mydao)

    if not api_user_id:
        raise InvalidApiKeyException

    api_user_doc = mydao.get(api_user_id)
    used_registration_spots = len(api_user_doc["registered_items"])
    remaining_registration_spots = api_user_doc["max_registered_items"] - used_registration_spots

    if remaining_registration_spots <= 0:
        logger.info("Did not register item {tiid} to {api_key} because limit exceeded".format(
            tiid=tiid, api_key=api_key))
        raise ApiLimitExceededException

    # do the registering

    alias_key = ":".join(alias)
    if alias_key in api_user_doc["registered_items"]:
        logger.info("Item {tiid} was already registered to {api_key}, {remaining_registration_spots} registration spots remain".format(
            tiid=tiid, api_key=api_key, remaining_registration_spots=remaining_registration_spots))
    else:        
        now = datetime.datetime.now().isoformat()
        api_user_doc["registered_items"][alias_key] = {
            "registered_date": now,
            "tiid": tiid
        }
        mydao.save(api_user_doc)

        used_registration_spots = len(api_user_doc["registered_items"])
        remaining_registration_spots = api_user_doc["max_registered_items"] - used_registration_spots

        logger.info("Registered item {tiid} to {api_key}, {remaining_registration_spots} registration spots remain".format(
            tiid=tiid, api_key=api_key, remaining_registration_spots=remaining_registration_spots))

    return(remaining_registration_spots)


def get_api_user_id_by_api_key(api_key, mydao):
    logger.debug("In get_api_user_by_api_key with {api_key}".format(
        api_key=api_key))

    # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults# for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
    res = mydao.view('api_users_by_api_key/api_users_by_api_key')

    matches = res[[api_key]] 

    api_user_id = None
    if matches.rows:
        api_user_id = matches.rows[0]["id"]
        logger.debug("found a match for {api_key}!".format(api_key=api_key))
    else:
        logger.debug("no match for api_key {api_key}!".format(api_key=api_key))
    return (api_user_id)


