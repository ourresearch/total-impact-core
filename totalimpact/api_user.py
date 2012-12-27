import datetime
import uuid

import logging
logger = logging.getLogger('ti.api_user')

def make(prefix, **meta):
    api_user_doc = {}

    new_api_key = prefix.upper() + str(uuid.uuid1())[0:6]
    now = datetime.datetime.now().isoformat()

    api_user_doc["created"] = now
    api_user_doc["type"] = "api_user"
    api_user_doc["meta"] = meta
    api_user_doc["current_key"] = new_api_key
    api_user_doc["key_history"] = {now: new_api_key}
    api_user_doc["max_registered_items"] = 1000
    api_user_doc["registered_items"] = {}

    return (api_user_doc, new_api_key)


def register_item(alias, tiid, api_key):
    if number_of_remaining_registration_spots(api_key) <= 0:
        #throw error
        pass

    # do the registering
    now = datetime.datetime.now().isoformat()

    api_user_doc["registered_items"][alias] = {
        "registered_date" = now,
        "tiid" = tiid
    }
    return(number_of_remaining_registration_spots)


def number_of_remaining_registration_spots(api_key):
    number_of_items_registered = len(api_user_doc["registered_items"])    
    number_of_items_remaining = api_user_doc["max_registered_items"] - number_of_items_registered
    return(number_of_items_remaining)



