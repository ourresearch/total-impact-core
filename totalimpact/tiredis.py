import redis, logging, json


logger = logging.getLogger("ti.tiredis")


def from_url(url, db=0):
    r = redis.from_url(url, db)
    return r

def set_num_providers_left(self, item_id, num_providers_left):
    logger.debug("setting {num} providers left to update for item '{tiid}'.".format(
        num=num_providers_left,
        tiid=item_id
    ))
    key = "num_providers_left:"+item_id
    self.set(key, num_providers_left)
    self.expire(key, 60*60*24)  # for a day    

def get_num_providers_left(self, item_id):
    r = self.get("num_providers_left:"+item_id)
    if r is None:
        return None
    else:
        return int(r)

def decr_num_providers_left(self, item_id, provider_name):
    num_providers_left = self.decr("num_providers_left:"+item_id)
    logger.info("bumped providers_run with %s for %s. %s left to run." % (
        provider_name, item_id, num_providers_left))
    return int(num_providers_left)

def add_to_alias_queue(self, tiid, aliases_dict, aliases_already_run=[]):
    queue_string = json.dumps([tiid, aliases_dict, aliases_already_run])
    logger.debug("adding item to queue ******* " + queue_string)
    self.lpush("aliasqueue", queue_string)

def set_memberitems_status(self, memberitems_key, query_status):
    key = "memberitems:"+memberitems_key 
    query_status_str = json.dumps(query_status)
    self.set(key, query_status_str)
    self.expire(key, 60*60*24)  # for a day    

def get_memberitems_status(self, memberitems_key):
    key = "memberitems:"+memberitems_key 
    try:
        query_status_str = self.get(key)
        query_status = json.loads(query_status_str)
    except TypeError:
        query_status = None
    return query_status

redis.Redis.set_num_providers_left = set_num_providers_left
redis.Redis.get_num_providers_left = get_num_providers_left
redis.Redis.decr_num_providers_left = decr_num_providers_left
redis.Redis.add_to_alias_queue = add_to_alias_queue
redis.Redis.set_memberitems_status = set_memberitems_status
redis.Redis.get_memberitems_status = get_memberitems_status





