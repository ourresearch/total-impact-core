import time
from provider import Provider
from totalimpact.model import Metrics
from BeautifulSoup import BeautifulStoneSoup

import logging
logger = logging.getLogger(__name__)

class Wikipedia(Provider):    
    def sleep_time(self):
        # FIXME: arbitrary
        sleep_length = 5
        logger.debug("Wikipedia:mentions: sleeping for " + str(5) + " seconds")
        return sleep_length
    
    def member_items(self, query_string): 
        raise NotImplementedError()
    
    def aliases(self, alias_object): 
        raise NotImplementedError()
        
    def metrics(self, alias_object):
        logger.info("Wikipedia:mentions: metrics requested for tiid:" + alias_object.tiid)
        metrics = Metrics()
        for alias in alias_object.get_aliases():
            if not self._is_supported(alias):
                continue
            logger.debug("Wikipedia:mentions: processing metrics for tiid:" + alias_object.tiid)
            self._get_metrics(alias, metrics)
        self._add_info(metrics)
        logger.debug("Wikipedia:mentions: final metrics for tiid " + alias_object.tiid + ": " + str(metrics))
        logger.info("Wikipedia:mentions: metrics completed for tiid:" + alias_object.tiid)
        return metrics
    
    def _is_supported(self, alias):
        return alias[0] in self.config.supported_namespaces
    
    def _get_metrics(self, alias, metrics):
        url = self.config.api % alias[1]
        logger.debug("Wikipedia:mentions: attempting to retrieve metrics from " + url)
        response = self.http_get(url)
        this_metrics = Metrics()
        self._extract_stats(response.content, this_metrics)
        self.show_details_url('http://en.wikipedia.org/wiki/Special:Search?search="' + alias[1] + '"&go=Go', this_metrics)
        metrics.add_metrics(this_metrics)
        logger.debug("Wikipedia:mentions: interrim metrics: " + str(metrics))
        
    def _extract_stats(self, content, metrics):
        print "extract stats"
        soup = BeautifulStoneSoup(content)
        try:
            articles = soup.search.findAll(title=True)
            metrics.add("mentions", len(articles))
        except AttributeError:
            # doesn't matter
            pass
    
    def _add_info(self, metrics):
        metrics.add("id", self.config.id)
        metrics.add("last_update", time.time())
        metrics.add("meta", self.config.meta)
