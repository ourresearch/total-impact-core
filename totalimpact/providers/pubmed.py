import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Metrics, ProviderMetric
from BeautifulSoup import BeautifulStoneSoup
import requests
import simplejson

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class PubmedMetricSnapshot(ProviderMetric):
    def __init__(self, provider, id, value):
        meta = provider.config.metrics["static_meta"][id]
        super(PubmedMetricSnapshot, self).__init__(id=id, value=value, meta=meta)

class Pubmed(Provider):  

    def __init__(self, config, app_config):
        super(Pubmed, self).__init__(config, app_config)
        self.id = self.config.id
        self.member_items_rx = re.compile(r"<Id>(.*)</Id>")

    def member_items(self, query_string, query_type):
        enc = urllib.quote(query_string)
        url = self.config.member_items["querytype"]["pubmedGrant"]['url'] % enc
        logger.debug(self.config.id + ": query type " + query_type)
        logger.debug(self.config.id + ": attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.member_items.get('timeout', None))

        hits = self.member_items_rx.findall(response.text)
        return [("PMID", hit) for hit in list(set(hits))]        
    



