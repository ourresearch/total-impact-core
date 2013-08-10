import redis, logging, json


logger = logging.getLogger("ti.tiredis")


def from_url(url, db=0):
    r = redis.from_url(url, db)
    return r

def decr_num_providers_left(self, item_id, provider_name):
    num_providers_left = self.decr("num_providers_left:"+item_id)
    logger.info(u"bumped providers_run for %s. %s left to run." % (
        item_id, num_providers_left))
    return int(num_providers_left)

def add_to_alias_queue(self, tiid, aliases_dict, aliases_already_run=[]):
    queue_string = json.dumps([tiid, aliases_dict, aliases_already_run])
    logger.debug(u"adding item to queue ******* {queue_string} /biblio_print".format(
        queue_string=queue_string))
    self.lpush("aliasqueue", queue_string)

def set_value(self, key, value, time_to_expire):
    json_value = json.dumps(value)
    self.set(key, json_value)
    self.expire(key, time_to_expire)

def get_value(self, key):
    try:
        json_value = self.get(key)
        value = json.loads(json_value)
    except TypeError:
        value = None
    return value

def set_num_providers_left(self, item_id, num_providers_left):
    logger.debug(u"setting {num} providers left to update for item '{tiid}'.".format(
        num=num_providers_left,
        tiid=item_id
    ))
    key = "num_providers_left:"+item_id
    expire = 60*60*24  # for a day    
    self.set_value(key, num_providers_left, expire)

def get_num_providers_left(self, item_id):
    key = "num_providers_left:"+item_id
    r = self.get_value(key)
    if r is None:
        return None
    else:
        return int(r)

def set_memberitems_status(self, memberitems_key, query_status):
    key = "memberitems:"+memberitems_key 
    expire = 60*60*24  # for a day    
    self.set_value(key, query_status, expire)

def get_memberitems_status(self, memberitems_key):
    key = "memberitems:"+memberitems_key 
    value = self.get_value(key)
    return value

def set_confidence_interval_table(self, size, level, table):
    key = "confidence_interval_table:{size},{level}".format(
        size=size, level=level)
    expire = 60*60*24*7  # for a week
    self.set_value(key, table, expire)

def get_confidence_interval_table(self, size, level):
    key = "confidence_interval_table:{size},{level}".format(
        size=size, level=level)
    value = self.get_value(key)
    return value

def set_reference_histogram_dict(self, genre, refset_name, year, table):
    key = "refset_histogram:{genre},{refset_name},{year}".format(
        genre=genre, refset_name=refset_name, year=year)
    expire = 60*60*24  # for a day    
    self.set_value(key, table, expire)

def get_reference_histogram_dict(self, genre, refset_name, year):
    key = "refset_histogram:{genre},{refset_name},{year}".format(
        genre=genre, refset_name=refset_name, year=year)
    value = self.get_value(key)
    return value

def set_reference_lookup_dict(self, genre, refset_name, year, table):
    key = "refset_lookup:{genre},{refset_name},{year}".format(
        genre=genre, refset_name=refset_name, year=year)
    expire = 60*60*24  # for a day    
    self.set_value(key, table, expire)

def get_reference_lookup_dict(self, genre, refset_name, year):
    key = "refset_lookup:{genre},{refset_name},{year}".format(
        genre=genre, refset_name=refset_name, year=year)
    value = self.get_value(key)
    return value

redis.Redis.set_value = set_value
redis.Redis.get_value = get_value
redis.Redis.set_num_providers_left = set_num_providers_left
redis.Redis.get_num_providers_left = get_num_providers_left
redis.Redis.decr_num_providers_left = decr_num_providers_left
redis.Redis.add_to_alias_queue = add_to_alias_queue
redis.Redis.set_memberitems_status = set_memberitems_status
redis.Redis.get_memberitems_status = get_memberitems_status
redis.Redis.set_confidence_interval_table = set_confidence_interval_table
redis.Redis.get_confidence_interval_table = get_confidence_interval_table
redis.Redis.set_reference_histogram_dict = set_reference_histogram_dict
redis.Redis.get_reference_histogram_dict = get_reference_histogram_dict
redis.Redis.set_reference_lookup_dict = set_reference_lookup_dict
redis.Redis.get_reference_lookup_dict = get_reference_lookup_dict





