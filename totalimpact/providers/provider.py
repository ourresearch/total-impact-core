from totalimpact.config import Configuration
from totalimpact.cache import Cache
import requests, os

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_definition, config):
        
        # first locate the config file
        cpath = provider_definition['config']
        if not os.path.isabs(cpath):
            cwd = os.getcwd()
            cpaths = []
            cpaths.append(os.path.join(cwd, cpath))
            if config.base_dir is not None:
                cpaths.append(os.path.join(config.base_dir, cpath))
            for p in cpaths:
                if os.path.isfile(p):
                    cpath = p
                    break
        
        if not os.path.isfile(cpath):
            raise ProviderConfigurationError()
        
        # if we get to here, go ahead and make the Provider object
        conf = Configuration(cpath, False)
        provider_class = config.get_class(provider_definition['class'])
        inst = provider_class(conf, config)
        return inst

class ProviderError(Exception):
    def __init__(self, response=None):
        self.response = response

class ProviderConfigurationError(ProviderError):
    pass

class ProviderTimeout(ProviderError):
    pass

class ProviderHttpError(ProviderError):
    pass

class ProviderClientError(ProviderError):
    pass

class ProviderServerError(ProviderError):
    pass

class ProviderContentError(ProviderError):
    pass

class ProviderState(object):
    def sleep_time():
        return 1

class Provider(object):

    def __init__(self, config, app_config):
        self.config = config
        self.app_config = app_config

    def provides_metrics(self): return False
    def member_items(self, query_string): raise NotImplementedError()
    def aliases(self, item): raise NotImplementedError()
    def metrics(self, item): raise NotImplementedError()
    
    def error(self, error, item):
        # FIXME: not yet implemented
        # all errors are handled by an incremental back-off and ultimate
        # escalation policy
        print "ERROR", type(error), item
    
    def sleep_time(self, dead_time=0):
        return 0
    
    def http_get(self, url, headers=None, timeout=None):
        # first thing is to try to retrieve from cache
        # FIXME: no idea what we'd get back from the cache...
        c = Cache()
        r = c.http_get(url)
        
        if r is not None:
            return content
            
        # ensure that a user-agent string is set
        if headers is None:
            headers = {}
        headers['User-Agent'] = self.app_config.user_agent
        
        # make the request
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            logger.debug("Attempt to connect to provider timed out during GET on " + url)
            raise ProviderTimeout()
        except requests.exceptions.RequestException as e:
            # general network error
            logger.info("RequestException during GET on: " + url)
            raise ProviderHttpError()
        
        # cache the response and return
        c.cache_http_get(url, r)
        return r
    
    """
    def get_cache_timeout_response(self,
                                    url,
                                    http_timeout_in_seconds = 20,
                                    max_cache_age_seconds = (1) * (24 * 60 * 60), # (number of days) * (number of seconds in a day),
                                    header_addons = {}):

        key = hashlib.md5(url).hexdigest()
        mc = memcache.Client(['127.0.0.1:11211'])
        response = mc.get(key)
        if response:
            self.status["count_got_response_from_cache"] += 1
        else:
            http = httplib2.Http(timeout=http_timeout_in_seconds)
            response = http.request(url)
            mc.set(key, response, max_cache_age_seconds)
            self.status["count_api_requests"] += 1

        # This is the old, file-based caching system.
        # I left some stuff out; Heather, feel free to move up.
        '''
        cache_read = http_cached.cache.get(url)
                self.status["count_got_response_from_cache"] += 1
        if (cache_read):
            (response, content) = cache_read.split("\r\n\r\n", 1)
        else:
            ## response['cache-control'] = "max-age=" + str(max_cache_age_seconds)
            ## httplib2._updateCache(header_dict, response, content, http_cached.cache, url)
            if response.fromcache:
            else:
                self.status["count_missed_cache"] += 1
                self.status["count_cache_miss_details"] = str(self.status["count_cache_miss_details"]) + "; " + url
                self.status["count_cache_miss_response"] = str(response)
                self.status["count_api_requests"] += 1

            if False:
                self.status["count_request_exception"] = "EXCEPTION!"
                self.status["count_uncached_call"] += 1
                self.status["count_api_requests"] += 1
                #(response, content) = http_cached.request(url, headers=header_dict.update({'cache-control':'no-cache'}))
                req = urllib2.Request(url, headers=header_dict)
                uh = urllib2.urlopen(req)
                content = uh.read()
                response = uh.info()
        '''

        return(response)
    """