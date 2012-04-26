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
        aliases = item.aliases.get_aliases_list(self.config.supported_namespaces)
        logger.info("{0}: found {1} good aliases for {2}"
            .format(self.config.id, len(aliases), item.id))

        if len(aliases) == 0:
            item.metrics = self._update_metrics_from_dict({"wikipedia:mentions": None}, item.metrics)

        for alias in aliases:
            logger.debug(self.config.id + ": processing metrics for tiid:" + item.id)
            logger.debug(self.config.id + ": looking for mentions of alias " + alias[1])
            new_metrics = self._get_metrics_for_id(alias[1])
            item.metrics = self._update_metrics_from_dict(new_metrics, item.metrics)

        logger.info("{0}: metrics completed for tiid {1}".format(self.config.id, item.id))
        return item
    
    def _get_metrics_for_id(self, id):
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
                    
        return self._extract_stats(response.text)

    
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
            
