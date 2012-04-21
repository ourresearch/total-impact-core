import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Aliases
from BeautifulSoup import BeautifulStoneSoup
import requests
import simplejson

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class Github(Provider):  

    def __init__(self, config):
        super(Github, self).__init__(config)
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

        return [("github", (query_string, hit)) for hit in list(set(hits))]
    

        
  


