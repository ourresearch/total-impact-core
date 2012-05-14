from totalimpact.cache import Cache
from totalimpact.dao import Dao
from totalimpact import providers

import requests, os, time, threading, sys, traceback, importlib, urllib

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_name):
        provider_module = importlib.import_module('totalimpact.providers.'+provider_name)
        provider = getattr(provider_module, provider_name.title())
        instance = provider()
        return instance

    @classmethod
    def get_providers(cls, config_providers):
        """ config is the application configuration """
        providers = []
        for provider_name, v in config_providers.iteritems():
            try:
                prov = ProviderFactory.get_provider(provider_name)
                prov.provider_name = provider_name
                providers.append(prov)
            except ProviderConfigurationError:
                logger.error("Unable to configure provider ... skipping " + str(v))
        return providers
        
class Provider(object):

    def __init__(self, max_cache_duration=86400, max_retries=999):
        self.max_cache_duration = max_cache_duration
        self.max_retries = max_retries
        self.provider_name = self.__class__.__name__.lower()

    def __repr__(self):
        return "Provider(%s)" % self.provider_name
    
    # API Methods
    # These should be filled in by each Provider implementing this signature

    # default method; providers can override
    def _get_error(self, response):
        if response.status_code >= 500:
            error = ProviderServerError
        else:
            error = ProviderClientError
        return(error)
    
    def _get_templated_url(self, template, id, method=None):
        url = template % id
        return(url)

    # default method; providers can override    
    def provenance_url(self, metric_name, aliases):
        # Returns the same provenance url for all metrics
        id = self.get_best_id(aliases)

        if id:
            provenance_url = self._get_templated_url(self.provenance_url_template, id)
        else:
            provenance_url = None

        return provenance_url

    # default method; providers can override
    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_members:
            raise NotImplementedError()

        logger.debug("Getting members for %s, %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        enc = urllib.quote(query_string)
        url = self._get_templated_url(provider_url_template, enc, "members")
        logger.debug("attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider  
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            error = self._get_error(response)
            raise error(response)

        # extract the member ids
        members = self._extract_members(response.text, query_string)

        return(members)

    # default method; providers can override
    def biblio(self, 
            aliases,
            provider_url_template=None):

        if not self.provides_biblio:
            raise NotImplementedError()

        id = self.get_best_id(aliases)

        # Only lookup biblio for items with appropriate ids
        if not id:
            logger.info("Not checking biblio because no relevant id for %s", self.provider_name)
            return None

        if not provider_url_template:
            provider_url_template = self.biblio_url_template

        return self.get_biblio_for_id(id, provider_url_template)

    # default method; providers can override
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_biblio:
            raise NotImplementedError()

        logger.debug("Getting biblio for %s, %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id)
        logger.debug("attempting to retrieve biblio from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)
        
        if response.status_code != 200:
            error = self._get_error(response)
            raise error(response)
        
        # extract the aliases
        biblio_dict = self._extract_biblio(response.text, id)

        return biblio_dict

    # default method; providers can override
    def aliases(self, 
            aliases, 
            provider_url_template=None):

        print "in aliases"
        if not self.provides_aliases:
            raise NotImplementedError()

        # Get a list of relevant aliases
        id_list = self.known_aliases(aliases)

        if not id_list:
            logger.info("Not checking aliases because no relevant id for %s", self.provider_name)
            return None

        new_aliases = aliases
        for id in id_list:
            logger.debug("processing alias %s" % id)
            print("processing alias %s" % id)
            print new_aliases
            new_aliases += self._get_aliases_for_id(id, provider_url_template)
            print new_aliases
        
        new_aliases_unique = list(set(new_aliases))
        return new_aliases_unique

    # default method; providers can override
    def _get_aliases_for_id(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        print "in _get_aliases_for_id"

        if not self.provides_aliases:
            raise NotImplementedError()

        logger.debug("Getting aliases for %s, %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        url = self._get_templated_url(provider_url_template, id)
        logger.debug("attempting to retrieve aliases from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            error = self._get_error(response)
            raise error(response)
        
        # extract the aliases
        new_aliases = self._extract_aliases(response.text, id)

        return new_aliases


    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None):

        if not self.provides_metrics:
            raise NotImplementedError()

        id = self.get_best_id(aliases)

        # Only lookup metrics for items with appropriate ids
        if not id:
            logger.info("Not checking metrics because no relevant id for %s", self.provider_name)
            return None

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        return self.get_metrics_for_id(id, provider_url_template)


    # default method; providers can override
    def get_metrics_for_id(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_metrics:
            raise NotImplementedError()

        logger.debug("Getting metrics for %s, %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.metrics_url_template
        url = self._get_templated_url(provider_url_template, id)
        logger.debug("attempting to retrieve metrics from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)
        
        if response.status_code != 200:
            error = self._get_error(response)
            raise error(response)
        
        # extract the metrics
        metrics_dict = self._extract_metrics(response.text, id)
        return metrics_dict


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

    @staticmethod
    def filter_aliases(aliases, supported_namespaces):
        aliases = ((ns,v) for (ns,v) in aliases if k == 'github')
    
    def http_get(self, url, headers=None, timeout=None, cache_enabled=True):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        from totalimpact.api import app

        # first thing is to try to retrieve from cache
        # use the cache if the config parameter is set and the arg allows it
        use_cache = app.config["CACHE_ENABLED"] and cache_enabled
        cache_data = None
        if use_cache:
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
            from totalimpact.api import app
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
        if use_cache:
            c.set_cache_entry(url, {'text' : r.text, 'status_code' : r.status_code})
        return r


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

    def __str__(self):
        return repr(self._message)


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

