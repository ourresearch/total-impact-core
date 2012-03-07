import time, re
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError
from totalimpact.models import Metrics
from BeautifulSoup import BeautifulStoneSoup
import requests

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class Dryad(Provider):  

    def __init__(self, config, app_config):
        super(Dryad, self).__init__(config, app_config)
        # self.state = DryadState(config)
        
        # All CrossRef DOI prefixes begin with "10" followed by a number of four or more digits
        # from http://www.crossref.org/02publishers/doi-guidelines.pdf
        # DOI_PATTERN = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)
        # CROSSREF_DOI_PATTERN = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)
        self.crossref_rx = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)

    def member_items(self, query_string): 
        raise NotImplementedError()
    
    def aliases(self, alias_object): 
        try:
            logger.info(self.config.id + ": aliases requested for tiid:" + alias_object.tiid)
            new_aliases = []
            for alias in alias_object.get_aliases_list(self.config.supported_namespaces):
                if not self._is_crossref_doi(alias):
                    continue
                logger.debug(self.config.id + ": processing aliases for tiid:" + alias_object.tiid)
                new_aliases += self._get_aliases(alias)
            logger.debug(self.config.id + ": discovered aliases for tiid " + alias_object.tiid + ": " + str(new_aliases))
            logger.info(self.config.id + ": aliases completed for tiid:" + alias_object.tiid)
            alias_object.add_unique(new_aliases)
            return alias_object
        except ProviderError as e:
            self.error(e, alias_object)
            return None
        
    def metrics(self, alias_object):
        raise NotImplementedError()

    def _is_crossref_doi(self, alias):
        # FIXME: Would exclude DataCite ids from here?
        return self.crossref_rx.search(alias[1]) != None

    def _get_aliases(self, alias):
        url = self.config.aliases['url'] % alias[1]
        logger.debug(self.config.id + ": attempting to retrieve aliases from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.aliases.get('timeout', None))
        
        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # extract the aliases
        new_aliases = self._extract_aliases(response.text)
        if new_aliases is not None:
            logger.debug(self.config.id + ": found aliases: " + str(new_aliases))
            return new_aliases
        return []
    
    def _extract_aliases(self, xml):
        soup = BeautifulStoneSoup(xml)
        try:
            return [("attacheddatadoi", soup.result.doc.arr.str.string)]
        except AttributeError:
            return None
    
class DryadState(object):
    pass
        