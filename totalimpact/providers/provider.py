from totalimpact.cache import Cache
from totalimpact.dao import Dao
from totalimpact import providers
from totalimpact import default_settings

import requests, os, time, threading, sys, traceback, importlib, urllib
import simplejson
import BeautifulSoup
from xml.dom import minidom 
from xml.parsers.expat import ExpatError


from totalimpact.tilogging import logging
logger = logging.getLogger("provider")


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

    @classmethod
    def get_all_static_meta(cls, config_providers=default_settings.PROVIDERS):
        # this is now duplicating get_all_metadata below; not high refactoring priority, though.
        all_static_meta = {}
        providers = cls.get_providers(config_providers)
        for provider in providers:
            if provider.provides_metrics:
                for metric_name in provider.static_meta_dict:
                    full_metric_name = provider.provider_name + ":" + metric_name
                    all_static_meta[full_metric_name] = provider.static_meta_dict[metric_name]
        return(all_static_meta)

    @classmethod
    def get_all_metadata(cls, config_providers=default_settings.PROVIDERS):
        ret = {}
        providers = cls.get_providers(config_providers)
        for provider in providers:
            provider_data = {}
            provider_data["provides_metrics"] = provider.provides_metrics
            provider_data["provides_aliases"] = provider.provides_aliases

            try:
                provider_data["metrics"] = provider.static_meta_dict
            except AttributeError:
                pass

            provider_name = provider.__class__.__name__.lower()

            ret[provider_name] = provider_data

        return ret


        
class Provider(object):

    def __init__(self, 
            max_cache_duration=86400, 
            max_retries=3, 
            tool_email="mytotalimpact@gmail.com"): 
        # FIXME change email to totalimpactdev@gmail.com after registering it with crossref
    
        self.max_cache_duration = max_cache_duration
        self.max_retries = max_retries
        self.tool_email = tool_email
        self.provider_name = self.__class__.__name__.lower()

    def __repr__(self):
        return "Provider(%s)" % self.provider_name
    
    # API Methods
    # These should be filled in by each Provider implementing this signature

    # default method; providers can override
    def _get_error(self, status_code, response=None):
        if status_code >= 500:
            error = ProviderServerError(response)
            logger.info("%20s ProviderServerError status code=%i, %s" 
                % (self.provider_name, status_code, str(response)))
        else:
            error = ProviderClientError(response)
            logger.info("%20s ProviderClientError status code=%i, %s" 
                % (self.provider_name, status_code, str(response)))

        raise(error)
        return error

    def _get_templated_url(self, template, id, method=None):
        url = template % id
        return(url)

    def relevant_aliases(self, aliases):
        filtered = [alias for alias in aliases 
                        if self.is_relevant_alias(alias)]
        #logger.info("relevant_aliases for %s are %s given %s" % (self.provider_name, str(filtered), str(aliases)))

        return filtered

    def get_best_id(self, aliases):
        filtered = self.relevant_aliases(aliases)
        if filtered:
            alias = filtered[0]
            (namespace, nid) = alias
        else:
            nid = None
        return(nid)

    @property
    def provides_members(self):
         return ("_extract_members" in dir(self))

    @property
    def provides_aliases(self):
         return ("_extract_aliases" in dir(self))

    @property
    def provides_biblio(self):
         return ("_extract_biblio" in dir(self))

    @property
    def provides_metrics(self):
         return ("_extract_metrics" in dir(self))

    @property
    def provides_static_meta(self):
         return ("static_meta_dict" in dir(self))


    # default method; providers can override    
    def metric_names(self):
        try:
            metric_names = self.static_meta_dict.keys()
        except AttributeError:
            metric_names = []
        return(metric_names)

    # default method; providers can override    
    def static_meta(self, metric_name):
        if not self.provides_static_meta:
            raise NotImplementedError()

        return(self.static_meta_dict[metric_name])
        

    # default method; providers can override    
    def provenance_url(self, metric_name, aliases):
        # Returns the same provenance url for all metrics
        id = self.get_best_id(aliases)

        if id:
            provenance_url = self._get_templated_url(self.provenance_url_template, id, "provenance")
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

        logger.debug("%20s getting member_items for %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        enc = urllib.quote(query_string)
        url = self._get_templated_url(provider_url_template, enc, "members")
        #logger.debug("attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider  
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            logger.warning("%20s WARNING, status_code=%i getting %s" 
                % (self.provider_name, response.status_code, url))            
            if response.status_code == 404:
                return {}
            else:
                self._get_error(response.status_code, response)

        # extract the member ids
        members = self._extract_members(response.text, query_string)

        return(members)

    # default method; providers can override
    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        if not self.provides_biblio:
            raise NotImplementedError()

        id = self.get_best_id(aliases)

        # Only lookup biblio for items with appropriate ids
        if not id:
            logger.info("%20s not checking biblio, no relevant alias" % (self.provider_name))
            return None

        if not provider_url_template:
            provider_url_template = self.biblio_url_template

        return self.get_biblio_for_id(id, provider_url_template, cache_enabled)

    # default method; providers can override
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_biblio:
            return {}

        logger.debug("%20s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)
        
        if response.status_code != 200:
            logger.warning("%20s WARNING, status_code=%i getting %s" 
                % (self.provider_name, response.status_code, url))            
            if response.status_code == 404:
                return {}
            else:
                self._get_error(response.status_code, response)
        
        # extract the aliases
        biblio_dict = self._extract_biblio(response.text, id)

        return biblio_dict

    # default method; providers can override
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        if not self.provides_aliases:
            raise NotImplementedError()

        # Get a list of relevant aliases
        relevant_aliases = self.relevant_aliases(aliases)

        if not relevant_aliases:
            logger.info("%20s not checking aliases, no relevant alias" % (self.provider_name))
            return []

        new_aliases = aliases[:]
        for alias in relevant_aliases:
            (namespace, nid) = alias
            new_aliases += self._get_aliases_for_id(nid, provider_url_template, cache_enabled)
        
        new_aliases_unique = list(set(new_aliases))

        return new_aliases_unique

    # default method; providers can override
    def _get_aliases_for_id(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_aliases:
            return []

        logger.debug("%20s getting aliases for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        url = self._get_templated_url(provider_url_template, id, "aliases")

        # try to get a response from the data provider                
        response = self.http_get(url, cache_enabled=cache_enabled)
        
        if response.status_code != 200:
            logger.warning("%20s WARNING, status_code=%i getting %s" 
                % (self.provider_name, response.status_code, url))            
            if response.status_code == 404:
                return []
            else:
                self._get_error(response.status_code, response)
        
        if not response.text:
            return []

        new_aliases = self._extract_aliases(response.text, id)
        return new_aliases


    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_metrics:
            raise NotImplementedError()

        id = self.get_best_id(aliases)

        # Only lookup metrics for items with appropriate ids
        if not id:
            logger.info("%20s not checking metrics, no relevant alias" % (self.provider_name))
            return {}

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        metrics = self.get_metrics_for_id(id, provider_url_template, cache_enabled)
        metrics_and_drilldown = {}
        for metric_name in metrics:
            drilldown_url = self.provenance_url(metric_name, aliases)
            metrics_and_drilldown[metric_name] = (metrics[metric_name], drilldown_url)

        return metrics_and_drilldown  


    # default method; providers can override
    def get_metrics_for_id(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_metrics:
            return {}

        logger.debug("%20s getting metrics for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.metrics_url_template
        url = self._get_templated_url(provider_url_template, id, "metrics")

        # try to get a response from the data provider                
        response = self.http_get(url, cache_enabled=cache_enabled)

        #logger.debug("get_metrics_for_id response.status_code %i" % response.status_code)
        
        # extract the metrics
        metrics_dict = self._extract_metrics(response.text, response.status_code, id=id)

        return metrics_dict


    # Core methods
    # These should be consistent for all providers

    def get_sleep_time(self, retry_count):
        max_retries = self.get_max_retries()

        # Check we haven't reached max retries
        if retry_count > max_retries:
            raise ValueError("Exceeded max retries %i" %max_retries)

        # exponential delay
        initial_delay = 1  # number of seconds for initial delay
        delay_time = initial_delay * 2**(retry_count-1)

        return delay_time
    
    def get_max_retries(self):
        return self.max_retries

    
    def http_get(self, url, headers=None, timeout=None, cache_enabled=True):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        from totalimpact.api import app

        # first thing is to try to retrieve from cache
        # use the cache if the config parameter is set and the arg allows it
        use_cache = app.config["CACHE_ENABLED"] and cache_enabled
        #logger.debug("http_get on %s with use_cache %i" %(url, use_cache))

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

def _load_json(page):
    try:
        data = simplejson.loads(page) 
    except simplejson.JSONDecodeError, e:
        raise ProviderContentMalformedError
    return(data)

def _lookup_json(data, keylist):
    for mykey in keylist:
        try:
            data = data[mykey]
        except KeyError:
            return None
    return(data)

def _extract_from_json(page, dict_of_keylists):
    data = _load_json(page)
    
    return_dict = {}
    if dict_of_keylists:
        for (metric, keylist) in dict_of_keylists.iteritems():
            value = _lookup_json(data, keylist)

            # only set metrics for non-zero and non-null metrics
            if value:
                return_dict[metric] = value
    return return_dict



def _lookup_xml_from_dom(doc, keylist):    
    for mykey in keylist:
        if not doc:
            return None

        try:
            doc_list = doc.getElementsByTagName(mykey)
            # just takes the first one for now
            doc = doc_list[0]
        except (KeyError, IndexError):
            return None
            
    if doc:      
        response = doc.firstChild.data
    else:
        response = None
    return(response)

def _lookup_xml_from_soup(soup, keylist):    
    smaller_bowl_of_soup = soup
    for mykey in keylist:
        if not smaller_bowl_of_soup:
            return None

        try:
            smaller_bowl_of_soup = smaller_bowl_of_soup.find(mykey)
        except KeyError:
            return None
            
    if smaller_bowl_of_soup:      
        response = smaller_bowl_of_soup.text
    else:
        response = None
    return(response)

def _extract_from_xml(page, dict_of_keylists):
    try:
        doc = minidom.parseString(page.strip().encode('utf-8'))
        lookup_function = _lookup_xml_from_dom
    except ExpatError, e:
        doc = BeautifulSoup.BeautifulStoneSoup(page) 
        lookup_function = _lookup_xml_from_soup

    if not doc:
        raise ProviderContentMalformedError

    return_dict = {}
    if dict_of_keylists:
        for (metric, keylist) in dict_of_keylists.iteritems():
            value = lookup_function(doc, keylist)

            # only set metrics for non-zero and non-null metrics
            if value:
                return_dict[metric] = value

    return return_dict





