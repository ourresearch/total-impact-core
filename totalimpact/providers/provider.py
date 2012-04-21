from totalimpact.config import Configuration
from totalimpact.cache import Cache
from totalimpact.dao import Dao
import requests, os, time, threading, sys, traceback

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_definition):
        """ Create an instance of a Provider object
        
            provider_definition is a dictionary which states the class and config file
            which should be used to create this provider. See totalimpact.conf.json 

            config is the application configuration
        """
        # directly beneath the working directory
        provider_config_path = os.path.join(os.getcwd(), provider_definition['config'])
        provider_config = Configuration(provider_config_path, False)
        provider_class_name = provider_definition['class']
        provider_class = provider_config.get_class(provider_class_name)
        inst = provider_class(provider_config)
        return inst
        
    @classmethod
    def get_providers(cls, config_providers):
        """ config is the application configuration """
        providers = []
        for p in config_providers:
            try:
                prov = ProviderFactory.get_provider(p)
                providers.append(prov)
            except ProviderConfigurationError:
                logger.error("Unable to configure provider ... skipping " + str(p))
        return providers
        
class Provider(object):

    def __init__(self, config):
        self.config = config
        self.name = 'Unknown Provider'

    def __repr__(self):
        return "Provider(%s)" % self.name
    
    # API Methods
    # These should be filled in by each Provider implementing this signature

    def provides_metrics(self): return False
    def member_items(self, query_string, query_type): raise NotImplementedError()
    def aliases(self, item): raise NotImplementedError()
    def metrics(self, item): raise NotImplementedError()
    def biblio(self, item): raise NotImplementedError()
    
    # Core methods
    # These should be consistent for all providers

    def get_sleep_time(self, error_type, retry_count):
        """ Find out how long we should sleep for the given error type and count
 
            error_type - timeout, http_error, ... should match config
            retry_count - this will be our n-th retry (first retry is 1)
        """
        error_conf = self.config.errors
        if error_conf is None:
            raise Exception("This provider has no config for error handling")

        conf = error_conf.get(error_type)
        if conf is None:
            raise Exception("This provider has no config for error handling for error type %s" % error_type)

        retries = conf.get("retries")
        if retries is None or retries == 0:
            raise exception

        delay = conf.get("retry_delay", 0)
        delay_cap = conf.get("delay_cap", -1)
        retry_type = conf.get("retry_type", "linear")

        # Check we haven't reached max retries
        if retry_count > retries and retries != -1:
            raise ValueError("Exceeded max retries for %s" % error_type)

        # Linear or exponential delay
        if retry_type == 'linear':
            delay_time = delay
        else:
            delay_time = delay * 2**(retry_count-1)

        # Apply delay cap, which limits how long we can sleep
        if delay_cap != -1:
            delay_time = min(delay_cap, delay_time)

        return delay_time
    
    def get_max_retries(self, error_type):
        error_conf = self.config.errors
        if error_conf is None:
            raise Exception("This provider has no config for error handling")

        conf = error_conf.get(error_type)
        if conf is None:
            raise Exception("This provider has no config for error handling for error type %s" % error_type)

        retries = conf.get("retries")
        if retries is None:
            return 0
        return retries

    def sleep_time(self, dead_time=0):
        return 0
    
    def http_get(self, url, headers=None, timeout=None, error_conf=None):
        return self.do_get(url, headers, timeout)
    
    def do_get(self, url, headers=None, timeout=None):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        # first thing is to try to retrieve from cache
        c = Cache(
            self.config.cache['max_cache_duration']
        )
        cache_data = c.get_cache_entry(url)
        if cache_data:
            # Return a stripped down equivalent of requests.models.Response
            # We don't store headers or other information here. If we need
            # that later, we can add it
            class CachedResponse:
                pass
            r = CachedResponse()
            r.status_code = cache_data['status_code']
            r.text = cache_data['text']
            return r
            
        # ensure that a user-agent string is set
        if headers is None:
            headers = {}
        
    # make the request
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as e:
            logger.debug("Attempt to connect to provider timed out during GET on " + url)
            raise ProviderTimeout("Attempt to connect to provider timed out during GET on " + url, e)
        except requests.exceptions.RequestException as e:
            logger.info("RequestException during GET on: " + url)
            raise ProviderHttpError("RequestException during GET on: " + url, e)
        
        # cache the response and return
        c.set_cache_entry(url, {'text' : r.text, 'status_code' : r.status_code})
        return r
    
    def _update_metrics_from_dict(self, new_metrics, old_metrics):
        for metric_name, metric_val in new_metrics.iteritems():
            old_metrics[metric_name]['values'][metric_val] = time.time()

            #TODO config should have different static_meta sections keyed by metric.
            old_metrics[metric_name]['static_meta'] = self.config.static_meta

        return old_metrics # now updated

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

class ProviderError(Exception):
    def __init__(self, message="", inner=None):
        self.message = message
        self.inner = inner
        # NOTE: experimental
        self.stack = traceback.format_stack()[:-1]
        
    def log(self):
        msg = " " + self.message + " " if self.message is not None and self.message != "" else ""
        wraps = "(inner exception: " + repr(self.inner) + ")"
        return self.__class__.__name__ + ":" + msg + wraps

class ProviderConfigurationError(ProviderError):
    pass

class ProviderTimeout(ProviderError):
    pass

class ProviderHttpError(ProviderError):
    pass

class ProviderClientError(ProviderError):
    def __init__(self, response, message="", inner=None):
        super(ProviderClientError, self).__init__(message, inner)
        self.response = response

class ProviderServerError(ProviderError):
    def __init__(self, response, message="", inner=None):
        super(ProviderServerError, self).__init__(message, inner)
        self.response = response

class ProviderContentMalformedError(ProviderError):
    pass
    
class ProviderValidationFailedError(ProviderError):
    pass

class ProviderRateLimitError(ProviderError):
    pass

