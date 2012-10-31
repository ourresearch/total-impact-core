 # -*- coding: utf-8 -*-  # need this line because test utf-8 strings later

from totalimpact.cache import Cache
from totalimpact.dao import Dao
from totalimpact import providers
from totalimpact import default_settings
from totalimpact import utils

import requests, os, time, threading, sys, traceback, importlib, urllib, logging, itertools
import simplejson
import BeautifulSoup
from xml.dom import minidom 
from xml.parsers.expat import ExpatError
import re

logger = logging.getLogger("ti.provider")

# Requests' logging is too noisy
requests_log = logging.getLogger("requests").setLevel(logging.WARNING) 

class ProviderFactory(object):

    @classmethod
    def get_provider(cls, provider_name):
        provider_module = importlib.import_module('totalimpact.providers.'+provider_name)
        provider = getattr(provider_module, provider_name.title())
        instance = provider()
        return instance

    @classmethod
    def get_providers(cls, config_providers, filter_by=None):
        """ config is the application configuration """
        providers = []
        for provider_name, v in config_providers:
            try:
                prov = ProviderFactory.get_provider(provider_name)
                prov.provider_name = provider_name
                providers.append(prov)

                if filter_by is not None:
                    if not getattr(prov, "provides_"+filter_by):
                        providers.pop()

            except ProviderConfigurationError:
                logger.error("Unable to configure provider ... skipping " + str(v))
        return providers

    @classmethod
    def num_providers_with_metrics(cls, config_providers):
        providers = cls.get_providers(config_providers)
        num_providers_with_metrics = 0
        for provider in providers:
            if provider.provides_metrics:
                num_providers_with_metrics += 1
        return num_providers_with_metrics

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
    def get_all_metric_names(cls, config_providers=default_settings.PROVIDERS):
        all_static_meta = cls.get_all_static_meta(config_providers)
        metric_names = all_static_meta.keys()
        return(metric_names)

    @classmethod
    def get_all_metadata(cls, config_providers=default_settings.PROVIDERS):
        ret = {}
        providers = cls.get_providers(config_providers)
        for provider in providers:
            provider_data = {}
            provider_data["provides_metrics"] = provider.provides_metrics
            provider_data["provides_aliases"] = provider.provides_aliases
            provider_data["url"] = provider.url
            provider_data["descr"] = provider.descr

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
            max_retries=0, 
            tool_email="mytotalimpact@gmail.com"): 
        # FIXME change email to totalimpactdev@gmail.com after registering it with crossref
    
        self.max_cache_duration = max_cache_duration
        self.max_retries = max_retries
        self.tool_email = tool_email
        self.provider_name = self.__class__.__name__.lower()
        self.logger = logging.getLogger("ti.providers." + self.provider_name)

    def __repr__(self):
        return "Provider(%s)" % self.provider_name
    
    # API Methods
    # These should be filled in by each Provider implementing this signature

    # default method; providers can override
    def _get_error(self, status_code, response=None):
        try:
            headers = response.headers
        except AttributeError:
            headers = {}
        try:
            text = response.text
        except (AttributeError, TypeError):
            text = ""           
        if status_code >= 500:
            error = ProviderServerError(response)
            self.logger.info("%s ProviderServerError status code=%i, %s, %s" 
                % (self.provider_name, status_code, text, str(headers)))
        else:
            error = ProviderClientError(response)
            self.logger.info("%s ProviderClientError status code=%i, %s, %s" 
                % (self.provider_name, status_code, text, str(headers)))

        raise(error)
        return error

    def _get_templated_url(self, template, id, method=None):
        if template != "%s":
            id = urllib.quote(id)
        url = template % id
        return(url)

    def relevant_aliases(self, aliases):
        filtered = [alias for alias in aliases 
                        if self.is_relevant_alias(alias)]
        #self.logger.debug("%s relevant_aliases are %s given %s" % (self.provider_name, str(filtered), str(aliases)))

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

        self.logger.debug("%s getting member_items for %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        url = self._get_templated_url(provider_url_template, query_string, "members")
        
        # try to get a response from the data provider  
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            self.logger.info("%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404:
                raise ProviderItemNotFoundError
            elif response.status_code == 303: #redirect
                pass                
            else:
                self._get_error(response.status_code, response)

        # extract the member ids
        try:
            members = self._extract_members(response.text, query_string)
        except (AttributeError, TypeError):
            members = []

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
            #self.logger.debug("%s not checking biblio, no relevant alias" % (self.provider_name))
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

        self.logger.debug("%s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            self.logger.info("%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404: #not found
                return {}
            elif response.status_code == 403: #forbidden
                return {}
            elif ((response.status_code >= 300) and (response.status_code < 400)): #redirect
                return {}
            else:
                self._get_error(response.status_code, response)
        
        # extract the aliases
        try:
            biblio_dict = self._extract_biblio(response.text, id)
        except (AttributeError, TypeError):
            biblio_dict = {}

        return biblio_dict

    # default method; providers can override
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        if not self.provides_aliases:
            #raise NotImplementedError()
            return []

        # Get a list of relevant aliases
        relevant_aliases = self.relevant_aliases(aliases)

        if not relevant_aliases:
            #self.logger.debug("%s not checking aliases, no relevant alias" % (self.provider_name))
            return []

        new_aliases = []
        for alias in relevant_aliases:
            (namespace, nid) = alias
            new_aliases += self._get_aliases_for_id(nid, provider_url_template, cache_enabled)
        
        # get uniques for things that are unhashable
        new_aliases_unique = [k for k,v in itertools.groupby(sorted(new_aliases))]

        return new_aliases_unique

    # default method; providers can override
    def _get_aliases_for_id(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_aliases:
            return []

        self.logger.debug("%s getting aliases for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        url = self._get_templated_url(provider_url_template, id, "aliases")

        # try to get a response from the data provider                
        response = self.http_get(url, cache_enabled=cache_enabled)
        
        if response.status_code != 200:
            self.logger.info("%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404:
                return []
            elif response.status_code == 403:  #forbidden
                return []
            elif response.status_code == 303: #redirect
                pass                
            else:
                self._get_error(response.status_code, response)

        try:       
            new_aliases = self._extract_aliases(response.text, id)
        except (TypeError, AttributeError):
            new_aliases = []

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
            #self.logger.debug("%s not checking metrics, no relevant alias" % (self.provider_name))
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

        self.logger.debug("%s getting metrics for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.metrics_url_template
        url = self._get_templated_url(provider_url_template, id, "metrics")

        # try to get a response from the data provider                
        response = self.http_get(url, cache_enabled=cache_enabled, allow_redirects=True)

        #self.logger.debug("%s get_metrics_for_id response.status_code %i" % (self.provider_name, response.status_code))
        
        # extract the metrics
        try:
            metrics_dict = self._extract_metrics(response.text, response.status_code, id=id)
        except (AttributeError, TypeError):  # throws type error if response.text is none
            metrics_dict = {}

        return metrics_dict


    # Core methods
    # These should be consistent for all providers
    
    def http_get(self, url, headers=None, timeout=20, cache_enabled=True, allow_redirects=False):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        from totalimpact import app

        # first thing is to try to retrieve from cache
        # use the cache if the config parameter is set and the arg allows it
        use_cache = app.config["CACHE_ENABLED"] and cache_enabled

        cache_data = None
        if headers:
            cache_key = headers.copy()
        else:
            cache_key = {}
        cache_key.update({"url":url, "allow_redirects":allow_redirects})
        if use_cache:
            c = Cache(self.max_cache_duration)
            cache_data = c.get_cache_entry(cache_key)
            if cache_data:
                class CachedResponse:
                    pass
                r = CachedResponse()
                r.status_code = cache_data['status_code']

                # Return a stripped down equivalent of requests.models.Response
                # We don't store headers or other information here. If we need
                # that later, we can add it
                # use it if it was a 200, otherwise go get it again
                if (r.status_code == 200):
                    r.url = cache_data['url']
                    r.text = cache_data['text']
                    self.logger.debug("returning from cache: %s" %(url))
                    return r
            
        # ensure that a user-agent string is set
        if headers is None:
            headers = {}
        headers["User-Agent"] = app.config["USER_AGENT"]
        
        # make the request        
        try:
            from totalimpact import app
            proxies = None
            if app.config["PROXY"]:
                proxies = {'http' : app.config["PROXY"], 'https' : app.config["PROXY"]}
            self.logger.debug("LIVE %s" %(url))
            r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, allow_redirects=allow_redirects, verify=False)
        except requests.exceptions.Timeout as e:
            self.logger.info("%s Attempt to connect to provider timed out during GET on %s" %(self.provider_name, url))
            raise ProviderTimeout("Attempt to connect to provider timed out during GET on " + url, e)
        except requests.exceptions.RequestException as e:
            raise ProviderHttpError("RequestException during GET on: " + url, e)

        if not r.encoding:
            r.encoding = "utf-8"            
        
        # cache the response and return
        if r and use_cache:
            cache_data = {'text' : r.text, 
                'status_code' : r.status_code, 
                'url': r.url}
            c.set_cache_entry(cache_key, cache_data)
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

class ProviderItemNotFoundError(ProviderError):
    pass
    
class ProviderValidationFailedError(ProviderError):
    pass

class ProviderRateLimitError(ProviderError):
    pass

def _load_json(page):
    try:
        data = simplejson.loads(page) 
    except simplejson.JSONDecodeError, e:
        logger.error("%s json decode fail '%s'. Here's the string: %s" %("_load_json", e.msg, page))
        raise ProviderContentMalformedError
    return(data)

def _lookup_json(data, keylist):
    for mykey in keylist:
        try:
            data = data[mykey]
        except (KeyError, TypeError):
            return None
    return(data)

def _extract_from_data_dict(data, dict_of_keylists):
    return_dict = {}
    if dict_of_keylists:
        for (metric, keylist) in dict_of_keylists.iteritems():
            value = _lookup_json(data, keylist)

            # only set metrics for non-zero and non-null metrics
            if value:
                return_dict[metric] = value
    return return_dict

def _extract_from_json(page, dict_of_keylists):
    data = _load_json(page)
    if not data:
        return {}
    return_dict = _extract_from_data_dict(data, dict_of_keylists)
    return return_dict

def _get_doc_from_xml(page):
    try:
        try:
            doc = minidom.parseString(page.strip().encode('utf-8'))
        except UnicodeDecodeError:
            doc = minidom.parseString(page.strip())            
        lookup_function = _lookup_xml_from_dom
    except ExpatError, e:
        doc = BeautifulSoup.BeautifulStoneSoup(page) 
        lookup_function = _lookup_xml_from_soup

    if not doc:
        raise ProviderContentMalformedError
    return (doc, lookup_function)

def _count_in_xml(page, mykey): 
    doc_list = _find_all_in_xml(page, mykey)
    if not doc_list:
        return 0
    count = len(doc_list)
    return(count)

def _find_all_in_xml(page, mykey):  
    (doc, lookup_function) = _get_doc_from_xml(page)  
    if not doc:
        return None
    try:
        doc_list = doc.getElementsByTagName(mykey)
    except (KeyError, IndexError, TypeError):
        return None
            
    return(doc_list)


def _lookup_xml_from_dom(doc, keylist): 
    response = None   
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
        try:
            response = doc.firstChild.data
        except AttributeError:
            return None
    try:
        response = int(response)
    except ValueError:
        pass
    return(response)

def _lookup_xml_from_soup(soup, keylist):    
    smaller_bowl_of_soup = soup
    for mykey in keylist:
        if not smaller_bowl_of_soup:
            return None
        try:
            # BeautifulSoup forces all keys to lowercase
            smaller_bowl_of_soup = smaller_bowl_of_soup.find(mykey.lower())
        except KeyError:
            return None
            
    if smaller_bowl_of_soup: 
        response = smaller_bowl_of_soup.text
    else:
        response = None

    try:
        response = int(response)
    except (ValueError, TypeError):
        pass

    return(response)

def _extract_from_xml(page, dict_of_keylists):
    (doc, lookup_function) = _get_doc_from_xml(page)
    return_dict = {}
    if dict_of_keylists:
        for (metric, keylist) in dict_of_keylists.iteritems():
            value = lookup_function(doc, keylist)

            # only set metrics for non-zero and non-null metrics
            if value:
                try:
                    value = value.strip()  #strip spaces if any
                except AttributeError:
                    pass
                return_dict[metric] = value

    return return_dict

# given a url that has a doi embedded in it, return the doi
def doi_from_url_string(url):
    logger.info("%s parsing url %s" %("doi_from_url_string", url))

    result = re.findall("(10\.\d+.[0-9a-wA-W_/\.\-%]+)" , url, re.DOTALL)
    try:
        doi = urllib.unquote(result[0])
    except IndexError:
        doi = None

    return(doi)


