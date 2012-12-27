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
    api_user_doc["registered_items"] = {}

    return (api_user_doc, new_api_key)




