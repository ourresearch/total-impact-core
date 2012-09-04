import redis, logging, json


logger = logging.getLogger("ti.tiredis")


def from_url(url):
    r = redis.from_url(url)
    return r

def set_num_providers_left(self, item_id, num_providers_left):
    logger.debug("setting {num} providers left to update for item '{tiid}'.".format(
        num=num_providers_left,
        tiid=item_id
    ))
    key = "num:"+item_id
    self.set(key, num_providers_left)
    self.expire(key, 60*60*24)  # for a day    

def get_num_providers_left(self, item_id):
    r = self.get("num:"+item_id)
    if r is None:
        return None
    else:
        return int(r)

def decr_num_providers_left(self, item_id, provider_name):
    num_providers_left = self.decr("num:"+item_id)
    logger.info("bumped providers_run with %s for %s. %s left to run." % (
        provider_name, item_id, num_providers_left))
    return int(num_providers_left)

def cache_collection(self, collection_doc):
    cid = collection_doc["_id"]
    logger.debug("caching collection {cid} into redis".format(cid=cid))
    key = "cid:"+cid
    self.set(key, json.dumps(collection_doc))
    self.expire(key, 60*60*24*7)  # for a week
    return True

def get_collection(self, cid):
    logger.debug("getting collection {cid} from redis".format(cid=cid))
    try:   
        collection_doc = json.loads(self.get("cid:"+cid))
    except TypeError:
        logger.debug("couldn't find collection {cid} in redis".format(cid=cid))
        collection_doc = None
    return collection_doc

def expire_collection(self, cid):
    logger.debug("expiring collection {cid} from redis".format(cid=cid))
    self.delete("cid:"+cid)
    return True

def add_to_alias_queue(self, tiid, aliases_dict, aliases_already_run=[]):
    queue_string = json.dumps([tiid, aliases_dict, aliases_already_run])
    logger.debug("adding item to queue ******* " + queue_string)
    self.lpush("aliasqueue", queue_string)



redis.Redis.set_num_providers_left = set_num_providers_left
redis.Redis.get_num_providers_left = get_num_providers_left
redis.Redis.decr_num_providers_left = decr_num_providers_left
redis.Redis.cache_collection = cache_collection
redis.Redis.get_collection = get_collection
redis.Redis.expire_collection = expire_collection
redis.Redis.add_to_alias_queue = add_to_alias_queue





