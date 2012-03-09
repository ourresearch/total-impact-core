from totalimpact.config import Configuration
from totalimpact.cache import Cache
import requests, os, time

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_definition, config):
        cpath = provider_definition['config']
        if not os.path.isabs(cpath):
            cwd = os.getcwd()
            cpaths = []
            
            # directly beneath the working directory
            cpaths.append(os.path.join(cwd, cpath))
            
            # in a config directory below the current one
            cpaths.append(os.path.join(cwd, "config", cpath))
            
            # in the directory as per the base_dir configuration
            if config.base_dir is not None:
                cpaths.append(os.path.join(config.base_dir, cpath))
            
            for p in cpaths:
                if os.path.isfile(p):
                    cpath = p
                    break
        if not os.path.isfile(cpath):
            raise ProviderConfigurationError()

        conf = Configuration(cpath, False)
        provider_class = config.get_class(provider_definition['class'])
        inst = provider_class(conf, config)
        return inst
        
    @classmethod
    def get_providers(cls, config):
        providers = []
        for p in config.providers:
            try:
                prov = ProviderFactory.get_provider(p, config)
                providers.append(prov)
            except ProviderConfigurationError:
                log.error("Unable to configure provider ... skipping " + str(p))
        return providers
        

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
    def __init__(self, rate_period=3600, rate_limit=350, 
                    time_fixture=None, last_request_time=None, request_count=0,
                    throttled=True):
        self.throttled = throttled
        self.time_fixture = time_fixture
        self.last_request_time = last_request_time
        self.rate_period = rate_period
        # scale the rate limit to avoid double counting
        self.rate_limit = rate_limit + 1
        self.request_count = request_count
    
    def register_unthrottled_hit(self):
        self.request_count += 1
    
    def _get_seconds(self, remaining_time, remaining_requests, request_time):
        if remaining_requests <= 0:
            # wait until the reset time
            return self._get_reset_time(request_time) - request_time
        return remaining_time / float(remaining_requests)
    
    # get the timestamp which represents when the rate counter will reset
    def _get_reset_time(self, request_time):
        # The reset time is at the start of the next rating period
        # after the time fixture.  If there is no time fixture,
        # then that time starts now
        if self.time_fixture is None:
            return request_time
        return self.time_fixture + self.rate_period
    
    def _rate_limit_expired(self, request_time):
        return self.time_fixture + self.rate_period <= request_time
    
    def _get_remaining_time(self, request_time):
        remaining_time = (self.time_fixture + self.rate_period) - request_time
        #since_last = request_time - self.last_request_time
        #remaining_time = self.rate_period - since_last
        return remaining_time
    
    def sleep_time(self):
        # some providers might have set themselves to be unthrottled
        if not self.throttled:
            return 0.0
        
        # set ourselves a standard time entity to use in all our
        # calculations
        request_time = time.time()
        
        # always pre-increment the request count, since we assume that we
        # are being called after the request, not before
        self.request_count += 1
        
        if self.last_request_time is None or self.time_fixture is None:
            # if there have been no previous requests, set the current last_request
            # time and the time_fixture to now
            self.time_fixture = request_time
            self.last_request_time = request_time
        
        # has the rate limiting period expired?  If so, set the new fixture
        # to now, and reset the request counter (which we start from 1,
        # for reasons noted above), and allow the caller to just go
        # right ahead by returning a 0.0
        if self._rate_limit_expired(request_time):
            self.time_fixture = request_time
            self.last_request_time = request_time
            self.request_count = 1
            return 0.0
        
        # calculate how many requests we have left in the current period
        # this number could be negative if the caller is ignoring our sleep
        # time suggestions
        remaining_requests = self.rate_limit - self.request_count
        
        # get the time remaining in this rate_period.  This does not take
        # into account whether the caller has obeyed our sleep time suggestions
        remaining_time = self._get_remaining_time(request_time)
        
        # NOTE: this will always return a number less than or equal to the time
        # until the next rate limit period is up.  It does not attempt to deal
        # with rate limit excessions
        #
        # calculate the amount of time to sleep for
        sleep_for = self._get_seconds(remaining_time, remaining_requests, request_time)
        
        # remember the time of /this/ request, so that it can be re-used 
        # on next call
        self.last_request_time = request_time
        
        # tell the caller how long to sleep for
        return sleep_for

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
