 # -*- coding: utf-8 -*-  # need this line because test utf-8 strings later

from totalimpact import cache as cache_module
from totalimpact import providers
from totalimpact import default_settings
from totalimpact import utils
from totalimpact import app
from totalimpact import db
from totalimpact.unicode_helpers import remove_nonprinting_characters

import requests, os, time, threading, sys, traceback, importlib, urllib, logging, itertools
import simplejson
import BeautifulSoup
import socket
import analytics
import re
from xml.dom import minidom 
from xml.parsers.expat import ExpatError
from sqlalchemy.sql import text    

logger = logging.getLogger("ti.provider")

# Requests' logging is too noisy
requests_log = logging.getLogger("requests").setLevel(logging.WARNING) 


class CachedResponse:
    def __init__(self, cache_data):
        self.status_code = cache_data['status_code']
        self.url = cache_data['url']
        self.text = cache_data['text']

def get_page_from_cache(url, headers, allow_redirects, cache):
    cache_key = headers.copy()
    cache_key.update({"url":url, "allow_redirects":allow_redirects})

    cache_data = cache.get_cache_entry(cache_key)
    # use it if it was a 200, otherwise go get it again
    if cache_data and (cache_data['status_code'] == 200):
        # logger.debug(u"returning from cache: %s" %(url))
        return CachedResponse(cache_data)
    return None

def store_page_in_cache(url, headers, allow_redirects, response, cache):
    cache_key = headers.copy()
    cache_key.update({"url":url, "allow_redirects":allow_redirects})

    cache_data = {
        'text':             response.text, 
        'status_code':      response.status_code, 
        'url':              response.url}
    cache.set_cache_entry(cache_key, cache_data)

def is_doi(nid):
    nid = nid.lower()
    if nid.startswith("doi:") or nid.startswith("10.") or "doi.org/" in nid:
        return True
    return False

def is_pmid(nid):
    if nid.startswith("pmid") or (len(nid)>2 and len(nid)<=8 and re.search("\d+", nid)):
        return True
    return False

def is_url(nid):
    if nid.lower().startswith("http://") or nid.lower().startswith("https://"):
        return True
    return False

def is_arxiv(nid):
    if nid.lower().startswith("arxiv:") or "arxiv.org/" in nid:
        return True
    return False

def normalize_alias(alias):
    (ns, nid) = alias
    if ns == "biblio":
        return (ns, nid)

    nid = remove_nonprinting_characters(nid)
    nid = nid.strip()  # also remove spaces
    if is_doi(nid):
        nid = providers.crossref.clean_doi(nid)
    elif is_pmid(nid):
        nid = providers.pubmed.clean_pmid(nid)
    elif is_arxiv(nid):
        nid = providers.arxiv.clean_arxiv_id(nid)
    elif is_url(nid):
        nid = providers.webpage.clean_url(nid)

    return (ns, nid)


def get_aliases_from_product_id_strings(product_id_strings):
    aliases = []
    for nid in product_id_strings:
        nid = remove_nonprinting_characters(nid)
        nid = nid.strip()  # also remove spaces
        if is_doi(nid):
            aliases += providers.crossref.Crossref().member_items(nid)
        elif is_pmid(nid):
            aliases += providers.pubmed.Pubmed().member_items(nid)
        elif is_arxiv(nid):
            aliases += providers.arxiv.Arxiv().member_items(nid)
        elif is_url(nid):
            aliases += providers.webpage.Webpage().member_items(nid)
    return aliases


def import_products(provider_name, import_input):
    if provider_name in ["bibtex", "product_id_strings"]:
        logger.debug(u"in import_products with {provider_name}".format(
            provider_name=provider_name))
    else:
        logger.debug(u"in import_products with {provider_name}: {import_input}".format(
            provider_name=provider_name, import_input=import_input))

    aliases = []

    # pull in standard items, if we were passed any of these
    if provider_name=="product_id_strings":
        aliases = get_aliases_from_product_id_strings(import_input["product_id_strings"])
    elif provider_name=="bibtex":
        provider = ProviderFactory.get_provider("bibtex")
        aliases = provider.member_items(import_input["bibtex"])
    else:
        try:
            provider = ProviderFactory.get_provider(provider_name)
            aliases = provider.member_items(import_input["account_name"])
        except ImportError:
            pass

    return(aliases)


def is_issn_in_doaj(issn):
    issn = issn.replace("-", "")
    raw_sql = text("""SELECT issn from doaj_issn_lookup where issn=:issn""")
    result = db.session.execute(raw_sql, params={
         "issn": issn
        })
    first_result = result.first()
    is_in_doaj = first_result != None
    return is_in_doaj

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
                logger.error(u"Unable to configure provider ... skipping " + str(v))
        return providers

    @classmethod
    def providers_with_metrics(cls, config_providers):
        providers = cls.get_providers(config_providers)
        providers_with_metrics = []
        for provider in providers:
            if provider.provides_metrics:
                providers_with_metrics += [provider.provider_name]
        return providers_with_metrics

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

            try:
                provider_data["url"] = provider.url
            except AttributeError:
                pass

            try:
                provider_data["descr"] = provider.descr
            except AttributeError:
                pass

            try:
                provider_data["metrics"] = provider.static_meta_dict
            except AttributeError:
                pass

            provider_name = provider.__class__.__name__.lower()

            ret[provider_name] = provider_data

        return ret


        
class Provider(object):

    def __init__(self, 
            max_cache_duration=60*15,  # 15 minutes
            max_retries=0, 
            tool_email="mytotalimpact@gmail.com"): 
        # FIXME change email to team@impactstory.org after registering it with crossref
    
        self.max_cache_duration = max_cache_duration
        self.max_retries = max_retries
        self.tool_email = tool_email
        self.provider_name = self.__class__.__name__.lower()
        self.max_simultaneous_requests = 20  # max simultaneous requests, used by backend        
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

        if response:
            url = response.url
        else:
            url = None

        # analytics.track("CORE", "Received error response from Provider", {
        #     "provider": self.provider_name, 
        #     "url": url,
        #     "text": text,
        #     "status_code": status_code
        #     })

        if status_code >= 500:
            error = ProviderServerError(response)
            self.logger.info(u"%s ProviderServerError status code=%i, %s, %s" 
                % (self.provider_name, status_code, text, str(headers)))
        else:
            error = ProviderClientError(response)
            self.logger.info(u"%s ProviderClientError status code=%i, %s, %s" 
                % (self.provider_name, status_code, text, str(headers)))

        raise(error)
        return error

    def _get_templated_url(self, template, id, method=None):
        try:
            id_unicode = unicode(id, "UTF-8")
        except TypeError:
            id_unicode = id
        id_utf8 = id_unicode.encode("UTF-8")

        substitute_id = id_utf8
        if template != "%s":
           substitute_id = urllib.quote(id_utf8)

        url = template % substitute_id
        return(url)

    def relevant_aliases(self, aliases):
        filtered = [alias for alias in aliases 
                        if self.is_relevant_alias(alias)]
        #self.logger.debug(u"%s relevant_aliases are %s given %s" % (self.provider_name, str(filtered), str(aliases)))

        return filtered

    def get_best_id(self, aliases):
        filtered = self.relevant_aliases(aliases)
        if filtered:
            alias = filtered[0]
            (namespace, nid) = alias
        else:
            nid = None
        return(nid)

    def get_best_url(self, aliases):
        filtered = self.relevant_aliases(aliases)
        if filtered:
            from totalimpact import item
            aliases_dict = item.alias_dict_from_tuples(aliases)

            if "doi" in aliases_dict:
                return u"http://doi.org/" + aliases_dict["doi"][0]
            if "pmid" in aliases_dict:
                return u"http://www.ncbi.nlm.nih.gov/pubmed/" + aliases_dict["pmid"][0]
            if "pmc" in aliases_dict:
                return u"http://www.ncbi.nlm.nih.gov/pmc/articles/" + aliases_dict["pmc"][0]
            if "url" in aliases_dict:
                return aliases_dict["url"][0]
        return None

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

    # default method; providers that use analytics credentials should override
    def uses_analytics_credentials(self, method_name):
         return False

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

        self.logger.debug(u"%s getting member_items for %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        url = self._get_templated_url(provider_url_template, query_string, "members")
        if not url:
            return []

        # try to get a response from the data provider  
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            self.logger.info(u"%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404:
                raise ProviderItemNotFoundError
            elif response.status_code == 303: #redirect
                pass                
            else:
                self._get_error(response.status_code, response)
        page = response.text

        # extract the member ids
        try:
            members = self._extract_members(page, query_string)
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
            #self.logger.debug(u"%s not checking biblio, no relevant alias" % (self.provider_name))
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

        self.logger.debug(u"%s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            self.logger.info(u"%s status_code=%i" 
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
            #self.logger.debug(u"%s not checking aliases, no relevant alias" % (self.provider_name))
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

        self.logger.debug(u"%s getting aliases for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        url = self._get_templated_url(provider_url_template, id, "aliases")

        # try to get a response from the data provider                
        response = self.http_get(url, cache_enabled=cache_enabled)
        
        if response.status_code != 200:
            self.logger.info(u"%s status_code=%i" 
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
            #self.logger.debug(u"%s not checking metrics, no relevant alias" % (self.provider_name))
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
            cache_enabled=True, 
            url_override=None,
            extract_metrics_method=None):

        if not self.provides_metrics:
            return {}

        if not extract_metrics_method:
            extract_metrics_method = self._extract_metrics

        # self.logger.debug(u"%s getting metrics for %s" % (self.provider_name, id))

        if url_override:
            url = url_override
        else:
            if not provider_url_template:
                provider_url_template = self.metrics_url_template
            url = self._get_templated_url(provider_url_template, id, "metrics")

        if not url:
            return {}

        # try to get a response from the data provider
        response = self.http_get(url, cache_enabled=cache_enabled, allow_redirects=True)

        #self.logger.debug(u"%s get_metrics_for_id response.status_code %i" % (self.provider_name, response.status_code))
        
        # extract the metrics
        try:
            metrics_dict = extract_metrics_method(response.text, response.status_code, id=id)
        except (requests.exceptions.Timeout, socket.timeout) as e:  # can apparently be thrown here
            self.logger.info(u"%s Provider timed out *after* GET in socket" %(self.provider_name))        
            raise ProviderTimeout("Provider timed out *after* GET in socket", e)        
        except (AttributeError, TypeError):  # throws type error if response.text is none
            metrics_dict = {}

        return metrics_dict

    # ideally would aggregate all tweets from all urls.  
    # the problem is this requires multiple drill-down links, which is troubling for UI at the moment
    # for now, look up all the alias urls and use metrics for url that is most tweeted
    def get_relevant_alias_with_most_metrics(self, metric_name, aliases, provider_url_template=None, cache_enabled=True):
        url_with_biggest_so_far = None
        biggest_so_far = 0
        url_aliases = []

        # also try adding a trailing slash to all of them, and a non trailing slash
        for (namespace, url) in self.relevant_aliases(aliases):
            if url.endswith("/"):
                url_aliases += [("url", url), ("url", re.sub("\/$", "", url))]
            else: 
                url_aliases += [("url", url), ("url", url+u"/")]

        for url_alias in url_aliases:
            (namespace, url) = url_alias
            metrics = self.get_metrics_for_id(url, provider_url_template, cache_enabled)
            if metric_name in metrics:
                if (metrics[metric_name] > biggest_so_far):
                    logger.debug(u"{new_url} has higher metrics than {prev_highest}".format(
                        new_url=url, prev_highest=url_with_biggest_so_far))
                    url_with_biggest_so_far = url
                    biggest_so_far = metrics[metric_name]
        return(url_with_biggest_so_far)
       

    # Core methods
    # These should be consistent for all providers
    
    def http_get(self, url, headers={}, timeout=20, cache_enabled=True, allow_redirects=False):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        headers["User-Agent"] = app.config["USER_AGENT"]

        if cache_enabled:
            cache = cache_module.Cache(self.max_cache_duration)
            cached_response = get_page_from_cache(url, headers, allow_redirects, cache)
            if cached_response:
                self.logger.debug(u"{provider_name} CACHE HIT on {url}".format(
                    provider_name=self.provider_name, url=url))
                return cached_response
            
        try:
            # analytics.track("CORE", "Sent GET to Provider", {"provider": self.provider_name, "url": url}, 
            #     context={ "providers": { 'Mixpanel': False } })
            try:
                self.logger.info(u"{provider_name} LIVE GET on {url}".format(
                    provider_name=self.provider_name, url=url))
            except UnicodeDecodeError:
                self.logger.info(u"{provider_name} LIVE GET on an url that throws UnicodeDecodeError".format(
                    provider_name=self.provider_name))

            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=allow_redirects, verify=False)
            if r and not r.encoding:
                r.encoding = "utf-8"     
            if r and cache_enabled:
                store_page_in_cache(url, headers, allow_redirects, r, cache)

        except (requests.exceptions.Timeout, socket.timeout) as e:
            self.logger.info(u"{provider_name} provider timed out on GET on {url}".format(
                provider_name=self.provider_name, url=url))
            # analytics.track("CORE", "Received no response from Provider (timeout)", 
            #     {"provider": self.provider_name, "url": url})
            raise ProviderTimeout("Provider timed out during GET on " + url, e)

        except requests.exceptions.RequestException as e:
            self.logger.info(u"{provider_name} RequestException on GET on {url}".format(
                provider_name=self.provider_name, url=url))
            # analytics.track("CORE", "Received RequestException from Provider", 
            #     {"provider": self.provider_name, "url": url})
            raise ProviderHttpError("RequestException during GET on: " + url, e)

        return r


    def http_get_multiple(self, urls, headers={}, timeout=20, cache_enabled=True, allow_redirects=False, num_concurrent_requests=False):
        """ Returns a requests.models.Response object or raises exception
            on failure. Will cache requests to the same URL. """

        headers["User-Agent"] = app.config["USER_AGENT"]

        # use the cache if the config parameter is set and the arg allows it
        if cache_enabled:
            cache = cache_module.Cache(self.max_cache_duration)

        responses = {}
        for url in urls:
            responses[url] = None
            if cache_enabled:
                cached_response = get_page_from_cache(url, headers, allow_redirects, cache)
                if cached_response:
                    responses[url] = cached_response

        uncached_urls = [url for url in responses if not responses[url]]

        # replace the loop below with requests made in parallel, ideally!
        fresh_responses = []
        fresh_responses_dict = {}
        for u in uncached_urls:
            fresh_responses += [self.http_get(u, headers=headers, timeout=timeout, allow_redirects=allow_redirects)]

        if fresh_responses:
            fresh_responses_dict = dict(zip(uncached_urls, fresh_responses))
            if cache_enabled:
                for url in fresh_responses_dict:
                    r = fresh_responses_dict[url]
                    if r and not r.encoding:
                        r.encoding = "utf-8"     
                    store_page_in_cache(url, headers, allow_redirects, r, cache)
        responses.update(fresh_responses_dict)
        return responses


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


class ProviderClientError(ProviderError):
    def __init__(self, message="", inner=None):
        super(ProviderClientError, self).__init__(message, inner)

class ProviderServerError(ProviderError):
    def __init__(self, message="", inner=None):
        super(ProviderServerError, self).__init__(message, inner)

class ProviderConfigurationError(ProviderError):
    pass

class ProviderTimeout(ProviderServerError):
    pass

class ProviderHttpError(ProviderError):
    pass

class ProviderContentMalformedError(ProviderClientError):
    pass

class ProviderItemNotFoundError(ProviderClientError):
    pass
    
class ProviderValidationFailedError(ProviderClientError):
    pass

class ProviderRateLimitError(ProviderClientError):
    pass

class ProviderAuthenticationError(ProviderClientError):
    pass

def _load_json(page):
    try:
        data = simplejson.loads(page) 
    except simplejson.JSONDecodeError, e:
        logger.error(u"%s json decode fail on '%s'" %("_load_json", e.msg))
        raise ProviderContentMalformedError
    return(data)

def _lookup_json(data, keylist):
    for mykey in keylist:
        try:
            data = data[mykey]
        except (KeyError, TypeError):
            return None
    return(data)

def _extract_from_data_dict(data, dict_of_keylists, include_falses=False):
    return_dict = {}
    if dict_of_keylists:
        for (metric, keylist) in dict_of_keylists.iteritems():
            value = _lookup_json(data, keylist)

            # unless include_falses, only set metrics for non-zero and non-null metrics
            if include_falses or (value and (value != "0")):
                return_dict[metric] = value
    return return_dict


def _extract_from_json(page, dict_of_keylists, include_falses=False):
    data = _load_json(page)
    if not data:
        return {}
    return_dict = _extract_from_data_dict(data, dict_of_keylists, include_falses)
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

def _metrics_dict_as_ints(metrics_dict):
    metrics_dict_ints = {key:int(val) for (key, val) in metrics_dict.items()}
    return metrics_dict_ints

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
    logger.info(u"%s parsing url %s" %("doi_from_url_string", url))

    result = re.findall("(10\.\d+.[0-9a-wA-W_/\.\-%]+)" , url, re.DOTALL)
    try:
        doi = urllib.unquote(result[0])
    except IndexError:
        doi = None

    return(doi)

def alias_dict_from_tuples(aliases_tuples):
    alias_dict = {}
    for (ns, ids) in aliases_tuples:
        if ns in alias_dict:
            alias_dict[ns] += [ids]
        else:
            alias_dict[ns] = [ids]
    return alias_dict
    
def strip_leading_http(url):
    response = re.sub(u"^https*://", "", url)
    return response

