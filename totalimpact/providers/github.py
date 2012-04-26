import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Aliases
from BeautifulSoup import BeautifulStoneSoup
import requests
import simplejson
import json

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
    
    def metrics(self, item):
        # get the alias object out of the item
        alias_object = item.aliases
        logger.info(self.config.id + ": metrics requested for tiid:" + item.id)

        # get the aliases that we want to check
        aliases = alias_object.get_aliases_list(self.config.supported_namespaces)
        if aliases is None or len(aliases) == 0:
            logger.debug(self.config.id + ": No acceptable aliases in tiid:" + item.id)
            logger.debug(self.config.id + ": Aliases: " + str(alias_object.get_aliases_list()))
            # Set all our metrics to None as we won't get a value here. This shows
            # that we've completed processing, otherwise we'd end up retrying
            for key in ['github:watchers','github:forks']:
                item.metrics[key]['static_meta'] = self.config.static_meta
                item.metrics[key]['values'][time.time()] = None
            return item

        # Just take the first alias. As I understand, we shouldn't find an item
        # with aliases for a repo, as these will not by the same Item
        alias = aliases[0]
        logger.debug(self.config.id + ": processing metrics for tiid:" + item.id)
        logger.debug(self.config.id + ": looking for mentions of alias " + alias[1])
        metrics = self.get_metrics_for_alias(alias)

        # add the static_meta info and values to the item
        for key in metrics.keys():
            value = metrics[key]
            item.metrics[key]['static_meta'] = self.config.static_meta
            item.metrics[key]['values'][time.time()] = metrics[key]

        # log our success (DEBUG and INFO)
        logger.debug(self.config.id + ": final metrics for tiid " + item.id + ": " + str(item.metrics))
        logger.info(self.config.id + ": metrics completed for tiid:" + item.id)

        return item

    def get_metrics_for_alias(self, alias):
        (namespace, val) = alias

        if namespace == 'github':
            url = self.config.metrics['url'] % val
            response = self.http_get(url)

            if response.status_code != 200:
                raise ProviderServerError

            data = json.loads(response.text) 
            metrics = {}
            metrics['github:watchers'] = data['repository']['watchers'] 
            metrics['github:forks'] = data['repository']['forks'] 
            return metrics
        else:
            # Currently only github is supported
            return {}


