import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Metrics, MetricSnap, Aliases
from BeautifulSoup import BeautifulStoneSoup
import requests
import simplejson

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class GithubMetricSnapshot(MetricSnap):
    def __init__(self, provider, id, value):
        static_meta = provider.config.metrics["static_meta"][id]
        super(GithubMetricSnapshot, self).__init__(id=id, value=value, static_meta=static_meta)

class Github(Provider):  

    def __init__(self, config, app_config):
        super(Github, self).__init__(config, app_config)
        self.id = self.config.id
        self.member_items_rx = re.compile(r"<Id>(.*)</Id>")
        
    def member_items(self, query_string, query_type):
        enc = urllib.quote(query_string)

        url = self.config.member_items["querytype"][query_type]['url'] % enc
        logger.debug(self.config.id + ": query type " + query_type)
        logger.debug(self.config.id + ": attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.member_items.get('timeout', None))
        
        #hits = self.github_member_items_rx.findall(response.text)
        hits = simplejson.loads(response.text)
        hits = [hit["name"] for hit in hits]

        return [(Aliases.NS.GITHUB, (query_string, hit)) for hit in list(set(hits))]
    

        
  


