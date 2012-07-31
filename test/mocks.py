import time, logging

from totalimpact.backend import StoppableThread
from totalimpact.providers.provider import Provider
from totalimpact.providers.provider import ProviderClientError, ProviderServerError
from totalimpact import ItemFactory

def dao_init_mock(self, config):
    pass

class MockDao(object):

    responses = []
    index = 0

    def get(self, id):
        ret = self.responses[self.index]
        self.index = self.index + 1
        return ret
    
    def setResponses(self, responses):
        self.responses = responses
        self.index = 0

    def save(self, doc):
        self.responses.append(doc)

    def view(self, viewname, **kwargs):
        return None


class InterruptTester(object):

    def run(self, stop_after=0):
        st = StoppableThread()
        st.start()
        
        time.sleep(stop_after)
        st.stop()
        st.join()


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
            item = ItemFactory.make()
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
        logging.debug("Saving item %s" % item.id)

    def add_to_metrics_queues(self, item):
        pass



class ProviderMock(Provider):
    """ Mock object to simulate a provider for testing 
    
        Allows generation of exceptions for when processing specific items, eg:
          metrics_exceptions = {
            1 : [ProviderTimeout],
            5 : [ProviderTimeout, ProviderRateLimitError]
          }
        This will then generate the relevant exceptions in sequence. Note an 
        exception will only be generated once, so once the method is retried
        it will generate the next exception, or succeed if no exceptions remain.

        You can obtain a list of items processed by this Provider by checking
        the metrics_processed or aliases_processed dictionaries

        Currently this needs to use "wikipedia:mentions", too hard to add in 
        a new metric type just for this class.
    """

    provider_name = "mock_provider"

    provides_members = True
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True
    url = "http://fakeproviderurl.com"

    def __init__(self, provider_name=None, metrics_exceptions=None, aliases_exceptions=None, biblio_exceptions=None):
        Provider.__init__(self, None)
        if provider_name:
            self.provider_name = provider_name
        else:
            self.provider_name = 'mock_provider'
        self.metrics_exceptions = metrics_exceptions
        self.aliases_exceptions = aliases_exceptions
        self.biblio_exceptions = biblio_exceptions
        self.metrics_processed = {}
        self.aliases_processed = {}
        self.biblio_processed = {}

    def metric_names(self):
        return(["wikipedia:mentions"])

    def aliases(self, aliases, url=None, cache_enabled=True):
        # If we are supplied a mock item, should have (mock, id) as it's
        # primary alias. Record that we have seen the item.
        # We cannot generate exceptions if it's not a mock as we won't
        # know what id to generate for.
        mock_aliases = [(k,v) for (k,v) in aliases if k == 'mock']
        if mock_aliases:
            (ns,val) = mock_aliases[0]
            item_id = int(val)
            if self.aliases_exceptions:
                if self.aliases_exceptions.has_key(item_id):
                    if len(self.aliases_exceptions[item_id]) > 0:
                        exc = self.aliases_exceptions[item_id].pop(0)
                        if exc in [ProviderClientError, ProviderServerError]:
                            raise exc('error')
                        else:
                            raise exc
            self.aliases_processed[item_id] = True
        return[('doi','test_alias')]

    def metrics(self, aliases, url=None, cache_enabled=True):
        """ Process metrics for the given aliases

            We should probably have been given a mockitem here. If so, then
            record the alias id under the 'mock' namespace'
        """
        # If we are supplied a mock item, should have (mock, id) as it's
        # primary alias. Record that we have seen the item.
        # We cannot generate exceptions if it's not a mock as we won't
        # know what id to generate for.
        mock_aliases = [(k,v) for (k,v) in aliases if k == 'mock']
        if mock_aliases:
            (ns,val) = mock_aliases[0]
            item_id = int(val)
            if self.metrics_exceptions:
                if self.metrics_exceptions.has_key(item_id):
                    if len(self.metrics_exceptions[item_id]) > 0:
                        exc = self.metrics_exceptions[item_id].pop(0)
                        if exc in [ProviderClientError, ProviderServerError]:
                            raise exc('error')
                        else:
                            raise exc
                self.metrics_processed[item_id] = True
        return {"wikipedia:mentions": (1, "http://drilldownurl.org")}

    def biblio(self, aliases, url=None, cache_enabled=True):
        """ Process biblio for the given aliases

            We should probably have been given a mockitem here. If so, then
            record the alias id under the 'mock' namespace'
        """
        # If we are supplied a mock item, should have (mock, id) as it's
        # primary alias. Record that we have seen the item.
        # We cannot generate exceptions if it's not a mock as we won't
        # know what id to generate for.
        mock_aliases = [(k,v) for (k,v) in aliases if k == 'mock']
        if mock_aliases:
            (ns,val) = mock_aliases[0]
            item_id = int(val)
            if self.biblio_exceptions:
                if self.biblio_exceptions.has_key(item_id):
                    if len(self.biblio_exceptions[item_id]) > 0:
                        exc = self.biblio_exceptions[item_id].pop(0)
                        if exc in [ProviderClientError, ProviderServerError]:
                            raise exc('error')
                        else:
                            raise exc
                self.biblio_processed[item_id] = True
        return {"title": "mock article name"}

        
