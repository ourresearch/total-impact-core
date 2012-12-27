from werkzeug import generate_password_hash, check_password_hash
import shortuuid, string, random, datetime
import csv, StringIO, json, uuid
from collections import OrderedDict, defaultdict

from totalimpact.models import ItemFactory
from totalimpact.providers.provider import ProviderFactory

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.collection')

def make(prefix, **meta):

    print meta

    new_api_key = prefix.upper() + str(uuid.uuid1())[0:6]

    now = datetime.datetime.now().isoformat()
    api_key_doc = {}

    api_key_doc["created"] = now
    api_key_doc["type"] = "api_user"
    api_key_doc["meta"] = meta
    api_key_doc["current_key"] = new_api_key
    api_key_doc["key_history"] = {now: new_api_key}
    api_key_doc["registered_items"] = {}

    return (api_key_doc, new_api_key)




