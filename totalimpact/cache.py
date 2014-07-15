import os
import sys
import hashlib
import logging
import json
from cPickle import PicklingError
import redis

from totalimpact import REDIS_CACHE_DATABASE_NUMBER

# set up logging
logger = logging.getLogger("ti.cache")

cache_client = redis.from_url(os.getenv("REDIS_URL"), REDIS_CACHE_DATABASE_NUMBER)

MAX_PAYLOAD_SIZE_BYTES = 1000*1000 # 1mb
MAX_CACHE_SIZE_BYTES = 100*1000*1000 #100mb

class CacheException(Exception):
    pass

class Cache(object):
    """ Maintains a cache of URL responses in memcached """

    def _build_hash_key(self, key):
        json_key = json.dumps(key)
        hash_key = hashlib.md5(json_key.encode("utf-8")).hexdigest()
        return hash_key

    def _get_client(self):
        return cache_client
 
    def __init__(self, max_cache_age=60*60):  #one hour
        self.max_cache_age = max_cache_age
        self.flush_cache()

    def flush_cache(self):
        #empties the cache
        mc = self._get_client()        
        # mc.flushdb()

    def get_cache_entry(self, key):
        """ Get an entry from the cache, returns None if not found """
        mc = self._get_client()
        hash_key = self._build_hash_key(key)
        response = mc.get(hash_key)
        if response:
            response = json.loads(response)
        return response

    def set_cache_entry(self, key, data):
        """ Store a cache entry """

        if sys.getsizeof(data["text"]) > MAX_PAYLOAD_SIZE_BYTES:
            logger.debug(u"Not caching because payload is too large")
            return None

        mc = self._get_client()

        if mc.info()["used_memory"] >= MAX_CACHE_SIZE_BYTES:
            logger.debug(u"Not caching because redis cache is too full")
            return None

        hash_key = self._build_hash_key(key)
        set_response = mc.set(hash_key, json.dumps(data))
        mc.expire(hash_key, self.max_cache_age)

        if not set_response:
            logger.warning("Unable to store into Redis. Make sure redis server is running.")
            raise CacheException("Unable to store into Redis. Make sure redis server is running.")
        return set_response
  
