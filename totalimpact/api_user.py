import datetime, shortuuid, os

from totalimpact import item

import logging
logger = logging.getLogger('ti.api_user')


class ApiLimitExceededException(Exception):
    pass

class InvalidApiKeyException(Exception):
    pass

class ItemAlreadyRegisteredToThisKey(Exception):
    pass

def is_current_api_user_key(key, mydao):
    if not key:
        return False

    api_user_id = get_api_user_id_by_api_key(key, mydao)
    if api_user_id:
        return True
    return False

def is_internal_key(key):
    if not key:
        return False

    if key in ["YOURKEY", "API-DOCS", os.getenv("API_KEY")]:
        return True
    return False

def is_valid_key(key, mydao):
    # do quick and common check first
    if is_internal_key(key):
        return True
    if is_current_api_user_key(key, mydao):
        return True
    return False


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

def is_registered(alias, api_key, mydao):
    if is_internal_key(api_key):
        return False

    alias = item.canonical_alias_tuple(alias)
    alias_string = ":".join(alias)
    api_key = api_key.lower()

    res = mydao.view('registered_items_by_alias/registered_items_by_alias')    
    matches = res[[alias_string, api_key]] 

    if matches.rows:
        #api_user_id = matches.rows[0]["id"]
        return True
    return False

def is_over_quota(api_key, mydao):
    if is_internal_key(api_key):
        return False

    api_user_id = get_api_user_id_by_api_key(api_key, mydao)
    api_user_doc = mydao.get(api_user_id)
    used_registration_spots = len(api_user_doc["registered_items"])
    remaining_registration_spots = api_user_doc["max_registered_items"] - used_registration_spots
    if remaining_registration_spots <= 0:
        return True
    return False


def add_registration_data(alias, tiid, api_key, mydao):
    if is_internal_key(api_key):
        return False

    alias_key = ":".join(alias)

    api_user_id = get_api_user_id_by_api_key(api_key, mydao)
    api_user_doc = mydao.get(api_user_id)

    now = datetime.datetime.now().isoformat()
    api_user_doc["registered_items"][alias_key] = {
        "registered_date": now,
        "tiid": tiid
    }
    mydao.save(api_user_doc)
    return True


def get_api_user_id_by_api_key(api_key, mydao):
    if is_internal_key(api_key):
        return None

    logger.debug("In get_api_user_by_api_key with {api_key}".format(
        api_key=api_key))

    # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults# for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
    res = mydao.view('api_users_by_api_key/api_users_by_api_key')

    api_key = api_key.lower()
    
    matches = res[[api_key]] 

    api_user_id = None
    if matches.rows:
        api_user_id = matches.rows[0]["id"]
        logger.debug("found a match for {api_key}!".format(api_key=api_key))
    else:
        logger.debug("no match for api_key {api_key}!".format(api_key=api_key))
    return (api_user_id)


def register_item(alias, api_key, myredis, mydao, mymixpanel=None):
    if not is_valid_key(api_key, mydao):
        raise InvalidApiKeyException
    if is_registered(alias, api_key, mydao):
        raise ItemAlreadyRegisteredToThisKey

    (namespace, nid) = alias
    tiid = item.get_tiid_by_alias(namespace, nid, mydao)
    if not tiid:
        if is_over_quota(api_key, mydao):
            raise ApiLimitExceededException
        else:
            tiid = item.create_item(namespace, nid, myredis, mydao, mymixpanel)
    registered = add_registration_data(alias, tiid, api_key, mydao)
    if registered and mymixpanel:
        mymixpanel.track("Create:Register", properties={"Namespace":namespace, 
                                                        "API Key":api_key}, ip=False)

    return tiid
