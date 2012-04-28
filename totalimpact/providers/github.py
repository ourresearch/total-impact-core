import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Aliases
from BeautifulSoup import BeautifulStoneSoup
import requests
import simplejson
import json

import logging
logger = logging.getLogger('providers.github')

class Github(Provider):  

    provider_name = "github"
    metric_names = ['github:watchers', 'github:forks']
    metric_namespaces = ["github"]
    alias_namespaces = []

    member_types = ['github_user']

    provides_members = True
    provides_aliases = False
    provides_metrics = True


    def __init__(self, config):
        super(Github, self).__init__(config)
        self.id = self.config.id
        
    def member_items(self, query_string, query_type):
        enc = urllib.quote(query_string)

        url = self.config.member_items["querytype"][query_type]['url'] % enc
        logger.debug("attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.member_items.get('timeout', None))
        if response.status_code != 200:
            raise ProviderServerError

        hits = simplejson.loads(response.text)
        hits = [hit["name"] for hit in hits]

        return [("github", (query_string, hit)) for hit in list(set(hits))]
    
    def metrics(self, aliases):

        if len(aliases) != 1:
            logger.warn("More than 1 github alias found, this should not happen. Will take first item.")

        # Just take the first alias. As I understand, we shouldn't find an item
        # with aliases for a repo, as these will not by the same Item
        alias = aliases[0]
        (namespace, val) = alias

        logger.debug("looking for mentions of alias (%s,%s)" % (namespace, val))

        url = self.config.metrics['url'] % val
        response = self.http_get(url)
        if response.status_code != 200:
            raise ProviderServerError

        data = json.loads(response.text) 
        return {
            'github:watchers' : data['repository']['watchers'],
            'github:forks' : data['repository']['forks']
        }


