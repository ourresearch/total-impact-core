from totalimpact.config import Configuration
from totalimpact.cache import Cache
from totalimpact.dao import Dao
import requests, os, time, threading, sys, traceback

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_definition):
        #TODO simplify. include conf params in providers, don't lookup paths to instantiate.

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
        for provider_name, v in config_providers.iteritems():
            try:
                prov = ProviderFactory.get_provider(v)
                prov.name = provider_name
                providers.append(prov)
            except ProviderConfigurationError:
                logger.error("Unable to configure provider ... skipping " + str(v))
        return providers
        
class Provider(object):

    def __init__(self, config):
        self.config = config

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
        """ Find out how long we should sleep for the given error type and count
 
            error_type - timeout, http_error, ... should match config
            retry_count - this will be our n-th retry (first retry is 1)
        """
        error_conf = self.config.errors
        if error_conf is None:
            raise ProviderConfigurationError("This provider has no config for error handling")

        conf = error_conf.get(error_type)
        if conf is None:
            raise ProviderConfigurationError("This provider has no config for error handling for error type %s" % error_type)

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
            raise ProviderConfigurationError("This provider has no config for error handling")

        conf = error_conf.get(error_type)
        if conf is None:
            raise ProviderConfigurationError("This provider has no config for error handling for error type %s" % error_type)

        retries = conf.get("retries")
        if retries is None:
            return 0
        return retries

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

