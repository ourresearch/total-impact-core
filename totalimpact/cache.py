import os
import sys
import pylibmc
import hashlib
import logging
import json
from cPickle import PicklingError

from totalimpact.utils import Retry

# set up logging
logger = logging.getLogger("ti.cache")

class CacheException(Exception):
    pass

class Cache(object):
    """ Maintains a cache of URL responses in memcached """

    def _build_hash_key(self, key):
        json_key = json.dumps(key)
        hash_key = hashlib.md5(json_key.encode("utf-8")).hexdigest()
        return hash_key

    def _get_memcached_client(self):
        servers = [os.environ.get('MEMCACHIER_SERVERS')]
        username=os.environ.get('MEMCACHIER_USERNAME')
        password=os.environ.get('MEMCACHIER_PASSWORD')
        if "localhost" in servers:
            username = None
            password = None
        mc = pylibmc.Client(
            servers=servers, 
            username=username,
            password=password,
            binary=True)
        return mc
 
    def __init__(self, max_cache_age=60*60):  #one hour
        self.max_cache_age = max_cache_age


    def flush_cache(self):
        #empties the cache
        mc = self._get_memcached_client()        
        mc.flush_all()

    @Retry(3, pylibmc.Error, 0.1)
    def get_cache_entry(self, key):
        """ Get an entry from the cache, returns None if not found """
        mc = self._get_memcached_client()
        hash_key = self._build_hash_key(key)
        response = mc.get(hash_key)
        return response

    @Retry(3, pylibmc.Error, 0.1)
    def set_cache_entry(self, key, data):
        """ Store a cache entry """

        #memcached will only store things up to 1MB as per http://sendapatch.se/projects/pylibmc/misc.html
        MAX_MEMCACHED_VALUE_SIZE = 1000*1000
        if sys.getsizeof(data["text"]) > MAX_MEMCACHED_VALUE_SIZE:
            logger.debug(u"Not caching because payload is too large")
            return None

        mc = self._get_memcached_client()
        hash_key = self._build_hash_key(key)
        try:
            set_response = mc.set(hash_key, data, time=self.max_cache_age)
            if not set_response:
                raise CacheException("Unable to store into Memcached. Make sure memcached server is running.")
        except PicklingError:
            # This happens when trying to cache a thread.lock object, for example.  Just don't cache.
            logger.debug(u"In set_cache_entry but got PicklingError")
            return None
        return set_response
  
