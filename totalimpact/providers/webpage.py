from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import lxml.html

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
        return("url" == namespace)


    # override because webpage doesn't throw timeouts, just get biblio if easy
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        logger.debug("%20s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider 
        try:      
            response = self.http_get(url, cache_enabled=cache_enabled)
        except provider.ProviderTimeout:
            logger.info("%20s ProviderTimeout getting %s so giving up on webpage biblio" 
                % (self.provider_name, id))
            return {}
        except provider.ProviderHttpError:
            logger.info("%20s ProviderHttpError getting %s so giving up on webpage biblio" 
                % (self.provider_name, id))
            return {}


        if response.status_code != 200:
            logger.info("%20s status_code=%i getting %s so giving up on webpage biblio" 
                % (self.provider_name, response.status_code, url))            
            return {}
        
        # extract the aliases
        biblio_dict = self._extract_biblio(response.text, id)

        return biblio_dict

    # use lxml because is html
    def _extract_biblio(self, page, id=None):
        biblio_dict = {}
        if not page:
            return biblio_dict
            
        parsed_html = lxml.html.document_fromstring(page.encode("utf-8"))
        
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

        return biblio_dict    
