import time, logging

from totalimpact.providers.provider import Provider
from totalimpact.providers.provider import ProviderClientError, ProviderServerError
from totalimpact import item



def dao_init_mock(self, config):
    pass

class MockDao(object):

    responses = []
    index = 0

    def get(self, id):
        ret = self.responses[self.index]
        self.index = self.index + 1
        return ret

    def __getitem__(self, item):
        return get(item)
    
    def setResponses(self, responses):
        self.responses = responses
        self.index = 0

    def save(self, doc):
        self.responses.append(doc)

    def view(self, viewname, **kwargs):
        return None






################################################################################
# TODO this class is TOTALLY BROKEN
# and will be until it's refactored to use the new, refactored items and alias
# dicts (no longer objects).
################################################################################
class QueueMock(object):

    def __init__(self, max_items = None):
        self.none_count = 0
        self.current_item = 0
        self.max_items = max_items
        self.items = {}
        self.thread_id = 'Queue Mock'
        self.queue_name = "Queue Mock"

    def first(self):
        if self.none_count >= 3:
            if self.max_items:
                if self.current_item > self.max_items:
                    return None
            # Generate a mock item with initial alias ('mock', id)
            item = item.make()
            item.id = self.current_item
            item.aliases['mock'] = str(item.id)
            self.items[self.current_item] = item
            return item
        else:
            self.none_count += 1
            return None

    def dequeue(self):
        item = self.first()
        if item:
            self.current_item += 1
        return item

    def save(self, item):
        logger.debug(u"Saving item %s" % item.id)

    def add_to_metrics_queues(self, item):
        pass



class ProviderMock(Provider):
    """ Mock object to simulate a provider for testing 

    """
    provides_members = True
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True

    metrics_returns = {
        "mock:pdf": (1, "http://drilldownurl.org"),
        "mock:html": (2, "http://drilldownurl.org")
    }
    aliases_returns = [('doi','10.1')]
    biblio_returns = {"title": "fake item"}

    exception_to_raise = None
    url = "http://fakeproviderurl.com"

    def __init__(self, provider_name=None):
        Provider.__init__(self, None)
        if provider_name:
            self.provider_name = provider_name
        else:
            self.provider_name = 'mock_provider'

    def metric_names(self):
        return(["wikipedia:mentions"])

    def aliases(self, aliases, url=None, cache_enabled=True):
        self._raise_preset_exception()
        return self.aliases_returns

    def metrics(self, aliases, url=None, cache_enabled=True):
        self._raise_preset_exception()
        return self.metrics_returns

    def biblio(self, aliases, url=None, cache_enabled=True):
        self._raise_preset_exception()
        return self.biblio_returns

    def _raise_preset_exception(self):
        if self.exception_to_raise:
            raise self.exception_to_raise
        
