import time
from provider import Provider
from provider import ProviderError, ProviderTimeout, ProviderServerError
from provider import ProviderClientError, ProviderHttpError, ProviderContentMalformedError
from BeautifulSoup import BeautifulStoneSoup
import requests

import logging
from xml.dom import minidom
from xml.parsers.expat import ExpatError

logger = logging.getLogger('providers.wikipedia')

class Wikipedia(Provider):  
    """ Gets numbers of citations for a DOI document from wikipedia using
        the Wikipedia search interface.
    """

    provider_name = "wikipedia"
    metric_names = ['wikipedia:mentions']
    metric_namespaces = ["doi"]
    alias_namespaces = None
    biblio_namespaces = None

    member_types = None

    provides_members = False
    provides_aliases = False
    provides_metrics = True
    provides_biblio = False

    def __init__(self, config):
        super(Wikipedia, self).__init__(config)

    def metrics(self, aliases):
        if len(aliases) != 1:
            logger.warn("More than 1 DOI alias found, this should not happen. Will process first item only.")
        
        (ns,val) = aliases[0] 

        logger.debug("looking for mentions of alias %s" % val)
        new_metrics = self._get_metrics_for_id(val)

        return new_metrics

    def _get_metrics_for_id(self, 
            id, 
            provider_url_template="http://localhost:8080/wikipedia/metrics&%s"):
        #url = self.config.metrics['url'] % id
        url = provider_url_template % id
    
        logger.debug("attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.metrics['timeout'], error_conf=self.config.errors)
        
        # client errors and server errors are not retried, as they usually 
        # indicate a permanent failure
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
                    
        return self._extract_stats(response.text)

    
    def _extract_stats(self, content):
        try:
            doc = minidom.parseString(content)
        except ExpatError, e:
            raise ProviderContentMalformedError("Content parse provider supplied XML document")

        searchinfo = doc.getElementsByTagName('searchinfo')
        if not searchinfo:
            raise ProviderContentMalformedError("No searchinfo in response document")
        val = searchinfo[0].attributes['totalhits'].value

        return {"wikipedia:mentions": int(val)}
            
