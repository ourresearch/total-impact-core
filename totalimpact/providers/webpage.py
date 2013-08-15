from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact import unicode_helpers

import lxml.html
import lxml.etree
import re

import logging
logger = logging.getLogger('ti.providers.webpage')

class Webpage(Provider):  

    example_id = ("url", "http://total-impact.org/")

    biblio_url_template = "%s"
    provenance_url_template = "%s"
    descr = "Information scraped from webpages by total-impact"
    url = "http://total-impact.org"


    def __init__(self):
        super(Webpage, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        is_relevant = (namespace in ["url", "biblio"])
        return(is_relevant)

    # copy biblio from aliases into item["biblio"] if no better source
    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        biblio = {}
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "biblio" in aliases_dict:
            biblio = aliases_dict["biblio"][0]
        elif "url" in aliases_dict:
            url = aliases_dict["url"][0]
            if not provider_url_template:
                provider_url_template = self.biblio_url_template
            biblio = self.get_biblio_for_id(url, provider_url_template, cache_enabled)

        return biblio


    # override because webpage doesn't throw timeouts, just get biblio if easy
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        logger.debug(u"%20s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider 
        try:      
            response = self.http_get(url, cache_enabled=cache_enabled)
        except provider.ProviderTimeout:
            logger.info(u"%20s ProviderTimeout getting %s so giving up on webpage biblio" 
                % (self.provider_name, id))
            return {}
        except provider.ProviderHttpError:
            logger.info(u"%20s ProviderHttpError getting %s so giving up on webpage biblio" 
                % (self.provider_name, id))
            return {}

        if response.status_code != 200:
            logger.info(u"%20s status_code=%i getting %s so giving up on webpage biblio" 
                % (self.provider_name, response.status_code, url))            
            return {}
        
        # extract the aliases
        try:
            biblio_dict = self._extract_biblio(response.text, id)
        except TypeError:  #sometimes has a response but no text in it
            return {}

        return biblio_dict

    # use lxml because is html
    def _extract_biblio(self, page, id=None):
        biblio_dict = {}

        if not page:
            return biblio_dict
        
        unicode_page = unicode_helpers.to_unicode_or_bust(page)
        try:
            parsed_html = lxml.html.document_fromstring(unicode_page)

            try:
                response = parsed_html.find(".//title").text
                if response:
                    biblio_dict["title"] = response.strip()
            except AttributeError:
                pass

            try:
                response = parsed_html.find(".//h1").text
                if response:
                    biblio_dict["h1"] = response.strip()
            except AttributeError:
                pass            

        # throws ParserError when document is empty        
        except (ValueError, lxml.etree.ParserError):
            logger.warning(u"%20s couldn't parse %s so giving up on webpage biblio" 
                            % (self.provider_name, id)) 
            try:
                response = re.search("<title>(.+?)</title>", unicode_page).group(1)
                response.replace("\n", "")
                response.replace("\r", "")
                if response:
                    biblio_dict["title"] = response.strip()
            except AttributeError:
                pass
        return biblio_dict    
