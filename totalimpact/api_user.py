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

    # make sure these are all lowercase because that is how they come in from flask
    if key.lower() in ["yourkey", "samplekey", "item-report-page", "api-docs", os.getenv("API_KEY").lower()]:
        return True
    return False

def is_valid_key(key, mydao):
    # do quick and common check first
    if is_internal_key(key):
        return True
    if is_current_api_user_key(key, mydao):
        return True
    return False

def save_api_user_to_database(new_api_key, max_registered_items, mydao, **meta):
    now = datetime.datetime.now().isoformat()
    cur = mydao.get_cursor()
    cur.execute("""INSERT INTO api_users 
                    (api_key, max_registered_items, created, planned_use, example_url, api_key_owner, notes, email, organization) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (new_api_key, max_registered_items, now, meta["planned_use"], meta["example_url"], meta["api_key_owner"], meta["notes"], meta["email"], meta["organization"]))
    cur.close()

def save_api_user(prefix, max_registered_items, mydao, **meta):
    new_api_key = prefix.lower() + "-" + shortuuid.uuid().lower()[0:6]
    save_api_user_to_database(new_api_key, max_registered_items, mydao, **meta)
    return (new_api_key)

def is_registered(alias, api_key, mydao):
    if is_internal_key(api_key):
        return False

    alias = item.canonical_alias_tuple(alias)
    alias_string = ":".join(alias)
    api_key = api_key.lower()

    cur = mydao.get_cursor()
    cur.execute("""SELECT 1 FROM registered_items 
            WHERE alias=%s AND lower(api_key)=%s""", 
            (alias_string, api_key))
    results = cur.fetchall()
    cur.close()

    if results:
        return True
    return False

def is_over_quota(api_key, mydao):
    if is_internal_key(api_key):
        return False

    used_registration_spots = 0 
    max_registered_items = 0 
    api_key = api_key.lower()   

    cur = mydao.get_cursor()
    cur.execute("""SELECT max_registered_items FROM api_users 
            WHERE lower(api_key)=%s""", 
            (api_key,))
    row = cur.fetchone()
    if row:
        max_registered_items = row["max_registered_items"]   

    cur.execute("""SELECT count(*) FROM registered_items 
            WHERE lower(api_key)=%s""", 
            (api_key,))
    row = cur.fetchone()
    if row:
        used_registration_spots = row[0]

    cur.close()

    remaining_registration_spots = max_registered_items - used_registration_spots
    if remaining_registration_spots <= 0:
        return True
    return False


def add_registration_data(alias, api_key, mydao):
    if is_internal_key(api_key):
        return False

    alias = item.canonical_alias_tuple(alias)
    alias_string = ":".join(alias)
    now = datetime.datetime.now().isoformat()

    cur = mydao.get_cursor()
    cur.execute("""INSERT INTO registered_items 
                    (api_key, alias, registered_date) 
                    VALUES (%s, %s, %s)""",
                (api_key, alias_string, now))
    cur.close()
    return True


def get_api_user_id_by_api_key(api_key, mydao):
    if is_internal_key(api_key):
        return None

    logger.debug("In get_api_user_by_api_key with {api_key}".format(
        api_key=api_key))
    api_key = api_key.lower()

    cur = mydao.get_cursor()
    cur.execute("""SELECT 1 FROM api_users 
            WHERE lower(api_key)=%s""", 
            (api_key,))
    results = cur.fetchall()
    cur.close()

    if results:
        logger.debug("found a match for {api_key}!".format(api_key=api_key))
        return api_key
    logger.debug("no match for api_key {api_key}!".format(api_key=api_key))
    return None


def register_item(alias, api_key, myredis, mydao, mypostgresdao):
    if not is_valid_key(api_key, mypostgresdao):
        raise InvalidApiKeyException
    if is_registered(alias, api_key, mypostgresdao):
        raise ItemAlreadyRegisteredToThisKey

    (namespace, nid) = alias
    tiid = item.get_tiid_by_alias(namespace, nid, mydao)
    if not tiid:
        if is_over_quota(api_key, mypostgresdao):
            raise ApiLimitExceededException
        else:
            tiid = item.create_item(namespace, nid, myredis, mydao)
    registered = add_registration_data(alias, api_key, mypostgresdao)

    return tiid
