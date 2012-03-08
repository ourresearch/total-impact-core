import time
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError
from totalimpact.models import ProviderMetric
from BeautifulSoup import BeautifulStoneSoup
import requests

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class Wikipedia(Provider):  

    def __init__(self, config, app_config):
        super(Wikipedia, self).__init__(config, app_config)
        self.state = WikipediaState(config)
        self.id = self.config.id

    def sleep_time(self, dead_time=0):
        sleep_length = self.state.sleep_time(dead_time)
        logger.debug(self.config.id + ": sleeping for " + str(5) + " seconds")
        return sleep_length
    
    def member_items(self, query_string): 
        raise NotImplementedError()
    
    def aliases(self, item): 
        raise NotImplementedError()

    def provides_metrics(self): return True
    
    def metrics(self, item):
        try:
            # get the alias object out of the item
            alias_object = item.aliases
            logger.info(self.config.id + ": metrics requested for tiid:" + alias_object.tiid)
            
            # construct the metrics object based on queries on each of the 
            # appropriate aliases
            metrics = ProviderMetric(id=self.config.id)
            for alias in alias_object.get_aliases_list(self.config.supported_namespaces):
                logger.debug(self.config.id + ": processing metrics for tiid:" + alias_object.tiid)
                self._get_metrics(alias, metrics)
            
            # add the meta info and other bits to the metrics object
            # FIXME: could probably combine this with the "show_details_url" in some way
            metrics.meta(self.config.meta)
            
            # log our success (DEBUG and INFO)
            logger.debug(self.config.id + ": final metrics for tiid " + alias_object.tiid + ": " + str(metrics))
            logger.info(self.config.id + ": metrics completed for tiid:" + alias_object.tiid)
            
            # finally update the item's metrics object with the new one, and return the item
            # FIXME: this will probably change to a call to item.metrics.add_provider_metric
            item.metrics().add_provider_metric(metrics)
            return item
        except ProviderError as e:
            self.error(e, item)
            return None
    
    def _get_metrics(self, alias, metrics):
        url = self.config.metrics['url'] % alias[1]
        logger.debug(self.config.id + ": attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.metrics['timeout'])
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # construct the metrics
        this_metrics = ProviderMetric(id=self.config.id)
        self._extract_stats(response.text, this_metrics)
        sdurl = self.config.metrics['provenance_url'] % alias[1]
        this_metrics.provenance(sdurl)
        
        # assign the metrics to the main metrics object
        metrics.sum(this_metrics)
        logger.debug(self.config.id + ": interim metrics: " + str(this_metrics))
        
    def _extract_stats(self, content, metrics):
        # FIXME: option to validate document...
        # FIXME: needs to re-queue after some specified wait (incremental back-off + escalation)
        soup = BeautifulStoneSoup(content)
        try:
            articles = soup.search.findAll(title=True)
            metrics.value(len(articles))
        except AttributeError:
            metrics.value(0)
            

class WikipediaState(object):
    
    def __init__(self, config):
        self.config = config
        
    def sleep_time(self, dead_time=0):
        # wikipedia has no rate limit
        return 0
    
