import redis, logging, json, datetime, os, iso8601
from collections import defaultdict

from totalimpact.providers.provider import ProviderFactory


logger = logging.getLogger("ti.tiredis")

def from_url(url, db=0):
    r = redis.from_url(url, db)
    return r

def set_hash_value(self, key, hash_key, value, time_to_expire, pipe=None):
    if not pipe:
        pipe = self
    json_value = json.dumps(value)
    pipe.hset(key, hash_key, json_value)
    pipe.expire(key, time_to_expire)

def get_hash_value(self, key, hash_key):
    try:
        json_value = self.hget(key, hash_key)
        value = json.loads(json_value)
    except TypeError:
        value = None
    return value

def get_all_hash_values(self, key):
    return self.hgetall(key)


def delete_hash_key(self, key, hash_key):
    return self.hdel(key, hash_key)


# don't use in production
def clear_currently_updating_status(self):
    # delete currently updating things, to start fresh
    currently_updating_keys = self.keys("currently_updating:*")
    for key in currently_updating_keys:
        self.delete(key)

def set_currently_updating(self, tiid, provider_name, value, pipe=None):
    if not pipe:
        pipe = self

    key = "currently_updating:{tiid}".format(
        tiid=tiid)
    expire = 60*60*24  # for a day    
    pipe.set_hash_value(key, provider_name, value, expire, pipe)

def get_currently_updating(self, tiid, provider_name):
    key = "currently_updating:{tiid}".format(
        tiid=tiid)
    return self.get_hash_value(key, provider_name)

def delete_currently_updating(self, tiid, provider_name):
    key = "currently_updating:{tiid}".format(
        tiid=tiid)
    return self.delete_hash_key(key, provider_name)


def init_currently_updating_status(self, tiids, providers):
    pipe = self.pipeline()    

    for tiid in tiids:
        # logger.debug(u"set_all_providers for '{tiid}'.".format(
        #     tiid=tiid))
        now = datetime.datetime.utcnow().isoformat()
        for provider_name in providers:
            currently_updating_status = {now: "in queue"}
            self.set_currently_updating(tiid, provider_name, currently_updating_status, pipe)
    pipe.execute()


def set_provider_started(self, item_id, provider_name):
    now = datetime.datetime.utcnow().isoformat()
    currently_updating_status = {now: "started"}
    self.set_currently_updating(item_id, provider_name, currently_updating_status)
    # logger.info(u"set_provider_started for %s %s" % (
    #     item_id, provider_name))


def set_provider_finished(self, item_id, provider_name):
    self.delete_currently_updating(item_id, provider_name)
    # logger.info(u"set_provider_finished for {tiid} {provider_name}".format(
    #     tiid=item_id, provider_name=provider_name))


def get_providers_currently_updating(self, item_id):
    key = "currently_updating:{tiid}".format(
        tiid=item_id)
    providers_currently_updating = self.get_all_hash_values(key)
    return providers_currently_updating


def get_num_providers_currently_updating(self, item_id):
    providers_currently_updating = self.get_providers_currently_updating(item_id)
    num_currently_updating = 0
    if not providers_currently_updating:
        # logger.info(u"In get_num_providers_currently_updating, no providers_currently_updating for {tiid}".format(
        #     tiid=item_id))
        pass
    for provider in providers_currently_updating:
        value = json.loads(providers_currently_updating[provider])
        last_update_time = iso8601.parse_date(value.keys()[0])
        now = datetime.datetime.utcnow()
        # from http://stackoverflow.com/questions/796008/cant-subtract-offset-naive-and-offset-aware-datetimes
        elapsed = now - last_update_time.replace(tzinfo=None)
        if elapsed < datetime.timedelta(hours=0, minutes=5):
            num_currently_updating += 1 
            # logger.warning(u"In get_num_providers_currently_updating, elapsed time still short, set currently_updating=True for {tiid}{provider}".format(
            #     tiid=item_id, provider=provider))
        else:
            # logger.warning(u"In get_num_providers_currently_updating, elapsed time is too long, set currently_updating=False for {tiid}{provider}".format(
            #     tiid=item_id, provider=provider))
            pass

    return num_currently_updating



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



redis.Redis.get_hash_value = get_hash_value
redis.Redis.get_all_hash_values = get_all_hash_values
redis.Redis.set_hash_value = set_hash_value
redis.Redis.delete_hash_key = delete_hash_key

redis.Redis.set_value = set_value
redis.Redis.get_value = get_value
redis.Redis.set_currently_updating = set_currently_updating
redis.Redis.get_currently_updating = get_currently_updating
redis.Redis.delete_currently_updating = delete_currently_updating
redis.Redis.clear_currently_updating_status = clear_currently_updating_status
redis.Redis.init_currently_updating_status = init_currently_updating_status
redis.Redis.set_provider_started = set_provider_started
redis.Redis.set_provider_finished = set_provider_finished
redis.Redis.get_providers_currently_updating = get_providers_currently_updating
redis.Redis.get_num_providers_currently_updating = get_num_providers_currently_updating
redis.Redis.set_memberitems_status = set_memberitems_status
redis.Redis.get_memberitems_status = get_memberitems_status
redis.Redis.set_confidence_interval_table = set_confidence_interval_table
redis.Redis.get_confidence_interval_table = get_confidence_interval_table
redis.Redis.set_reference_histogram_dict = set_reference_histogram_dict
redis.Redis.get_reference_histogram_dict = get_reference_histogram_dict
redis.Redis.set_reference_lookup_dict = set_reference_lookup_dict
redis.Redis.get_reference_lookup_dict = get_reference_lookup_dict


