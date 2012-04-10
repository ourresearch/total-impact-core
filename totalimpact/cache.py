import hashlib
import memcache

class CacheException(Exception):
    pass

class Cache(object):
    """ Maintains a cache of URL responses in memcached """

    def __init__(self, max_cache_age=86400):
        self.max_cache_age = max_cache_age

    def get_cache_entry(self, url):
        """ Get an entry from the cache, returns None if not found """
        key = hashlib.md5(url).hexdigest()
        mc = memcache.Client(['127.0.0.1:11211'])
        return mc.get(key)

    def set_cache_entry(self, url, data):
        """ Store a cache entry """
        key = hashlib.md5(url).hexdigest()
        mc = memcache.Client(['127.0.0.1:11211'])
        if not mc.set(key,data,time=self.max_cache_age):
            raise CacheException("Unable to store into Memcached. Check config.")
        
        
