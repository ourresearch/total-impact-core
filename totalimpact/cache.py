import os
import pylibmc
import hashlib
import logging
from cPickle import UnpickleableError

# set up logging
logger = logging.getLogger("ti.cache")

class CacheException(Exception):
    pass

class Cache(object):
    """ Maintains a cache of URL responses in memcached """

    def __init__(self, max_cache_age=86400):
        self.max_cache_age = max_cache_age

    def get_cache_entry(self, url):
        """ Get an entry from the cache, returns None if not found """
        key = hashlib.md5(url.encode("utf-8")).hexdigest()
        mc = pylibmc.Client(
		    servers=[os.environ.get('MEMCACHE_SERVERS')],
		    username=os.environ.get('MEMCACHE_USERNAME'),
		    password=os.environ.get('MEMCACHE_PASSWORD'),
		    binary=True)
        return mc.get(key)

    def set_cache_entry(self, url, data):
        """ Store a cache entry """
        key = hashlib.md5(url.encode("utf-8")).hexdigest()
        mc = pylibmc.Client(
		    servers=[os.environ.get('MEMCACHE_SERVERS')],
		    username=os.environ.get('MEMCACHE_USERNAME'),
		    password=os.environ.get('MEMCACHE_PASSWORD'),
		    binary=True)
        try:
            set_response = mc.set(key, data, time=self.max_cache_age)
            if not set_response:
                raise CacheException("Unable to store into Memcached. Make sure memcached server is running.")
        except UnpickleableError:
            # This happens when trying to cache a thread.lock object, for example.  Just don't cache.
            logger.debug("In set_cache_entry with " + url + " but got Unpickleable Error")
            set_response = None
        return (set_response)
  
        
        
