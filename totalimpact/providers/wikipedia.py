import time
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError
from totalimpact.models import Metrics
from BeautifulSoup import BeautifulStoneSoup
import requests

import logging
logger = logging.getLogger(__name__)

class Wikipedia(Provider):  

    def __init__(self, config, app_config):
        super(Wikipedia, self).__init__(config, app_config)
        self.state = WikipediaState(config)

    def sleep_time(self, dead_time=0):
        sleep_length = self.state.sleep_time(dead_time)
        logger.debug("Wikipedia:mentions: sleeping for " + str(5) + " seconds")
        return sleep_length
    
    def error(self, error, alias_object):
        # FIXME: not yet implemented
        # all errors are handled by an incremental back-off and ultimate
        # escalation policy
        print "ERROR", type(error), alias_object
    
    def member_items(self, query_string): 
        raise NotImplementedError()
    
    def aliases(self, alias_object): 
        raise NotImplementedError()
        
    def metrics(self, alias_object):
        try:
            logger.info("Wikipedia:mentions: metrics requested for tiid:" + alias_object.tiid)
            metrics = Metrics()
            for alias in alias_object.get_aliases_list(self.config.supported_namespaces):
                logger.debug("Wikipedia:mentions: processing metrics for tiid:" + alias_object.tiid)
                self._get_metrics(alias, metrics)
            self._add_info(metrics)
            logger.debug("Wikipedia:mentions: final metrics for tiid " + alias_object.tiid + ": " + str(metrics))
            logger.info("Wikipedia:mentions: metrics completed for tiid:" + alias_object.tiid)
            return metrics
        except ProviderError as e:
            self.error(e, alias_object)
            return None
    
    def _get_metrics(self, alias, metrics):
        url = self.config.api % alias[1]
        logger.debug("Wikipedia:mentions: attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url)
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # construct the metrics
        this_metrics = Metrics()
        self._extract_stats(response.content, this_metrics)
        self.show_details_url('http://en.wikipedia.org/wiki/Special:Search?search="' + alias[1] + '"&go=Go', this_metrics)
        
        # assign the metrics to the main metrics object
        metrics.add_metrics(this_metrics)
        logger.debug("Wikipedia:mentions: interrim metrics: " + str(metrics))
        
    def _extract_stats(self, content, metrics):
        # FIXME: option to validate document...
        # FIXME: needs to re-queue after some specified wait (incremental back-off + escalation)
        soup = BeautifulStoneSoup(content)
        try:
            articles = soup.search.findAll(title=True)
            metrics.add("mentions", len(articles))
        except AttributeError:
            metrics.add("mentions", 0)
    
    def _add_info(self, metrics):
        metrics.add("id", self.config.id)
        metrics.add("last_update", time.time())
        metrics.add("meta", self.config.meta)

class WikipediaState(object):
    
    def __init__(self, config):
        self.config = config
        
    def sleep_time(self, dead_time=0):
        # wikipedia has no rate limit
        return 0
    
