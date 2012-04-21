import time
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState, ProviderContentMalformedError, ProviderValidationFailedError
from BeautifulSoup import BeautifulStoneSoup
import requests

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class Wikipedia(Provider):  

    def __init__(self, config):
        super(Wikipedia, self).__init__(config)
        self.id = self.config.id

    def member_items(self, query_string):
        raise NotImplementedError()
    
    def aliases(self, item): 
        raise NotImplementedError()

    def provides_metrics(self): return True
    
    def metrics(self, item):
        # get the alias object out of the item
        alias_object = item.aliases
        logger.info(self.config.id + ": metrics requested for tiid:" + item.id)
        
        # get the aliases that we want to check
        aliases = alias_object.get_aliases_list(self.config.supported_namespaces)
        print aliases
        if aliases is None or len(aliases) == 0:
            logger.debug(self.config.id + ": No acceptable aliases in tiid:" + item.id)
            logger.debug(self.config.id + ": Aliases: " + str(alias_object.__dict__))
            return item
        
        # if there are aliases to check, carry on
        for alias in aliases:
            logger.debug(self.config.id + ": processing metrics for tiid:" + item.id)
            logger.debug(self.config.id + ": looking for mentions of alias " + alias[1])
            item.metrics = self._update_metrics_from_id(item.metrics, alias[1])
        
        # log our success (DEBUG and INFO)
        logger.debug(self.config.id + ": final metrics for tiid " + item.id + ": "
            + str(item.metrics))
        logger.info(self.config.id + ": metrics completed for tiid:" + item.id)
        
        return item
    
    def _update_metrics_from_dict(self, new_metrics, old_metrics):
        #TODO all Providers will use this method; move it up to the parent class.
        for metric_name, metric_val in new_metrics.iteritems():
            old_metrics[metric_name]['values'][metric_val] = time.time()

            #TODO config should have different static_meta sections keyed by metric.
            old_metrics[metric_name]['static_meta'] = self.config.static_meta

        return old_metrics # now updated
    
    def _update_metrics_from_id(self, metrics, id):
        #TODO this should take an alias in other Providers (esp. Mendeley),
        # since there will be different API calls and extract_stats methods
        # for different alias namespaces. Should actually think about making new
        # classes/subclasses to do this.
    
        # FIXME: urlencoding?
        url = self.config.metrics['url'] % id 
        logger.debug(self.config.id + ": attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.metrics['timeout'], error_conf=self.config.errors)
        
        # client errors and server errors are not retried, as they usually 
        # indicate a permanent failure
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
                    
        new_metric_values = self._extract_stats(response.text)
        metrics = self._update_metrics_from_dict(new_metric_values, metrics)
        
        return metrics
    
    def _extract_stats(self, content):
        try:
            soup = BeautifulStoneSoup(content)
        except:
            # seems this pretty much never gets called, as soup will happily
            # try to parse just about anything you throw at it.
            raise ProviderContentMalformedError("Content cannot be parsed into soup")
        
        try:
            articles = soup.search.findAll(title=True)
            val = len(articles)
        except AttributeError:
            # NOTE: this does not raise a ProviderValidationError, because missing
            # articles are not indicative of a formatting failure - there just might
            # not be any articles
            val = 0

        return {"wikipedia:mentions": val}
            
