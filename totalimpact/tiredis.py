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



def set_task_id(self, tiid, task_id, pipe=None):
    if not pipe:
        pipe = self

    key = "tiid_task_id:{tiid}".format(
        tiid=tiid)
    expire = 60*60*24  # for a day    
    pipe.set_value(key, task_id, expire, pipe)    


def get_task_id(self, tiid, pipe=None):
    if not pipe:
        pipe = self

    key = "tiid_task_id:{tiid}".format(
        tiid=tiid)
    return self.get_value(key, pipe)


def set_tiid_task_ids(self, tiid_task_ids):
    print "******** setting tasks", tiid_task_ids
    pipe = self.pipeline()    

    for (tiid, task_id) in tiid_task_ids.iteritems():
        self.set_task_id(tiid, task_id, pipe)
    pipe.execute()    

def get_tiid_task_ids(self, tiids):
    pipe = self.pipeline()    
    tiid_task_ids = {}

    for tiid in tiids:
        tiid_task_ids[tiid] = self.get_task_id(tiid, pipe)
    pipe.execute()  
    print "******** got tasks", tiid_task_ids

    return tiid_task_ids


def set_value(self, key, value, time_to_expire, pipe=None):
    if not pipe:
        pipe = self

    json_value = json.dumps(value)
    pipe.set(key, json_value)
    pipe.expire(key, time_to_expire)

def get_value(self, key, pipe=None):
    if not pipe:
        pipe = self

    try:
        json_value = pipe.get(key)
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
redis.Redis.set_memberitems_status = set_memberitems_status
redis.Redis.get_memberitems_status = get_memberitems_status
redis.Redis.set_confidence_interval_table = set_confidence_interval_table
redis.Redis.get_confidence_interval_table = get_confidence_interval_table
redis.Redis.set_reference_histogram_dict = set_reference_histogram_dict
redis.Redis.get_reference_histogram_dict = get_reference_histogram_dict
redis.Redis.set_reference_lookup_dict = set_reference_lookup_dict
redis.Redis.get_reference_lookup_dict = get_reference_lookup_dict
redis.Redis.set_tiid_task_ids = set_tiid_task_ids
redis.Redis.get_tiid_task_ids = get_tiid_task_ids
redis.Redis.get_task_id = get_task_id
redis.Redis.set_task_id = set_task_id


