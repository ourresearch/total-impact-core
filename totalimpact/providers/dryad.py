import time
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError
from totalimpact.models import Metrics
from BeautifulSoup import BeautifulStoneSoup
import requests

import logging
logger = logging.getLogger(__name__)

class Dryad(Provider):  

    def __init__(self, config, app_config):
        super(Dryad, self).__init__(config, app_config)
        # self.state = DryadState(config)

    def member_items(self, query_string): 
        raise NotImplementedError()
    
    def aliases(self, alias_object): 
        raise NotImplementedError()
        
    def metrics(self, alias_object):
        raise NotImplementedError()


class DryadState(object):
    pass
        