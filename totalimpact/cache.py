
class CacheException(Exception):
    pass

class Cache(object):
    """ Maintains a cache of URL responses in memcached """

    def __init__(self, max_cache_age=86400):
        self.max_cache_age = max_cache_age

    def get_cache_entry(self, url):

        return None


    def set_cache_entry(self, url, data):

        return True

  
        
        
