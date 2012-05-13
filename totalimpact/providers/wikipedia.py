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

    metric_names = ['wikipedia:mentions']
    metric_namespaces = ["doi"]
    alias_namespaces = None
    biblio_namespaces = None

    member_types = None

    provides_members = False
    provides_aliases = False
    provides_metrics = True
    provides_biblio = False

    provenance_url_template = "http://en.wikipedia.org/wiki/Special:Search?search='%s'&go=Go"
    metrics_url_template = "http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch='%s'"


    def __init__(self):
        super(Wikipedia, self).__init__()

    def metrics(self, 
            aliases,             
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        if len(aliases) != 1:
            logger.warn("More than 1 DOI alias found, this should not happen. Will process first item only.")
        
        (ns,val) = aliases[0] 

        logger.debug("looking for mentions of alias %s" % val)
        new_metrics = self._get_metrics_for_id(val, provider_url_template)

        return new_metrics

    def _get_metrics_for_id(self, id, provider_url_template):
        url = provider_url_template % id
    
        logger.debug("attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url)
        
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
            
    def provenance_url(self, metric_name, aliases):
        # Wikipedia returns the same provenance url for all metrics
        # so ignoring the metric name
        (ns, id) = aliases[0]

        if id:
            provenance_url = self.provenance_url_template % id
        else:
            provenance_url = None

        return provenance_url
