from totalimpact.config import Configuration
from totalimpact.cache import Cache
from totalimpact.dao import Dao
from totalimpact import providers
import requests, os, time, threading, sys, traceback, importlib

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_name):
        provider_module = importlib.import_module('totalimpact.providers.'+provider_name)
        provider = getattr(provider_module, provider_name.title())

        instance = provider(Configuration("totalimpact/providers/"+provider_name+".conf.json"))


        return instance


        
    @classmethod
    def get_providers(cls, config_providers):
        """ config is the application configuration """
        providers = []
        for provider_name, v in config_providers.iteritems():
            try:
                prov = ProviderFactory.get_provider(provider_name)
                prov.name = provider_name
                providers.append(prov)
            except ProviderConfigurationError:
                logger.error("Unable to configure provider ... skipping " + str(v))
        return providers
        
class Provider(object):

    def __init__(self, config, max_cache_duration=86400, max_retries=999):
        self.config = config
        self.max_cache_duration = max_cache_duration
        self.max_retries = max_retries

    def __repr__(self):
        return "Provider(%s)" % self.provider_name
    
    # API Methods
    # These should be filled in by each Provider implementing this signature

    def member_items(self, query_string, query_type): raise NotImplementedError()
    def aliases(self, aliases): raise NotImplementedError()
    def metrics(self, aliases): raise NotImplementedError()
    def biblio(self, aliases): raise NotImplementedError()
    
    # Core methods
    # These should be consistent for all providers

    def get_sleep_time(self, error_type, retry_count):
        """ How long we should sleep for the given error type and count
 
            error_type - timeout, http_error, ... should match config
            retry_count - this will be our n-th retry (first retry is 1)
        """

        max_retries = self.get_max_retries(error_type)

        # Check we haven't reached max retries
        if retry_count > max_retries:
            raise ValueError("Exceeded max retries for %s" % error_type)

        # exponential delay
        initial_delay = 1  # number of seconds for initial delay
        delay_time = initial_delay * 2**(retry_count-1)

        return delay_time
    
    def get_max_retries(self, error_type):
        # give up right away if a content_malformed error
        if error_type in ["content_malformed"]:
            max_retries = 0
        else:  
            # For other error types, try as up to max_retries times.
            # Other errors include timeout, http_error, client_server_error, 
            #    rate_limit_reached, validation_failed
            max_retries = self.max_retries
        return max_retries

    def sleep_time(self, dead_time=0):
        return 0
    
    def http_get(self, url, headers=None, timeout=None, error_conf=None):
        return self.do_get(url, headers, timeout)

    @staticmethod
    def filter_aliases(aliases, supported_namespaces):
        aliases = ((ns,v) for (ns,v) in aliases if k == 'github')
    
    def do_get(self, url, headers=None, timeout=None):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        from totalimpact.api import app

        # first thing is to try to retrieve from cache
        cache_data = None
        if app.config["CACHE_ENABLED"]:
            c = Cache(self.max_cache_duration)
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
            proxies = None
            if app.config["PROXY"]:
                proxies = {'http' : app.config["PROXY"], 'https' : app.config["PROXY"]}
            r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies)
        except requests.exceptions.Timeout as e:
            logger.debug("Attempt to connect to provider timed out during GET on " + url)
            raise ProviderTimeout("Attempt to connect to provider timed out during GET on " + url, e)
        except requests.exceptions.RequestException as e:
            logger.info("RequestException during GET on: " + url)
            raise ProviderHttpError("RequestException during GET on: " + url, e)
        
        # cache the response and return
        if app.config["CACHE_ENABLED"]:
            c.set_cache_entry(url, {'text' : r.text, 'status_code' : r.status_code})
        return r

    def _update_metrics_from_dict(self, new_metrics, old_metrics):
        now_str = str(int(time.time()))
        for metric_name, metric_val in new_metrics.iteritems():
            old_metrics[metric_name]['values'][now_str] = metric_val

            #TODO config should have different static_meta sections keyed by metric.
            old_metrics[metric_name]['static_meta'] = self.config.static_meta

        return old_metrics # now updated


class ProviderError(Exception):
    def __init__(self, message="", inner=None):
        self._message = message  # naming it self.message raises DepreciationWarning
        self.inner = inner
        # NOTE: experimental
        self.stack = traceback.format_stack()[:-1]
        
    # DeprecationWarning: BaseException.message has been deprecated 
    #   as of Python 2.6 so implement property here
    @property
    def message(self): 
        return (self._message)

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

