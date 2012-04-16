import os, unittest, time

from totalimpact.backend import StoppableThread
from totalimpact.config import Configuration, StringConfiguration

from totalimpact.providers.provider import Provider
from totalimpact.providers.provider import ProviderConfigurationError, ProviderTimeout, ProviderHttpError
from totalimpact.providers.provider import ProviderClientError, ProviderServerError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderValidationFailedError, ProviderRateLimitError

def dao_init_mock(self, config):
    pass

class MockDao(object):

    def get(self, id):
        ret = self.responses[self.index]
        self.index = self.index + 1
        self.saved = []
        return ret
    
    def setResponses(self, responses):
        self.responses = responses
        self.index = 0

    def save(self, doc):
        self.save.append(doc)





class InterruptTester(object):
    def run(self, stop_after=0):
        st = StoppableThread()
        st.start()
        
        time.sleep(stop_after)
        st.stop()
        st.join()

class QueueMock(object):
    def __init__(self, max_items = None):
        self.none_count = 0
        self.current_item = 0
        self.max_items = max_items
    def first(self):
        if self.none_count >= 3:
            if self.max_items:
                if self.current_item > self.max_items:
                    return None
            return ItemMock(self.current_item)
        else:
            self.none_count += 1
            return None
    def save_and_unqueue(self, item):
        self.current_item += 1

class ItemMock(object):
    pass
    def __init__(self,id=None):
        self.id = id
    def __repr__(self):
        return "ItemMock(%s)" % self.id

base_provider_conf = StringConfiguration('''
{
    "errors" : {
        "http_timeout" : { "retries" : 3, "retry_delay" : 0.1, "retry_type" : "linear", "delay_cap" : -1 },
        "http_error" : { "retries" : 3, "retry_delay" : 0.1, "retry_type" : "linear", "delay_cap" : -1 },
        "client_server_error" : { "retries" : 0, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
        "rate_limit_reached" : { "retries" : -1, "retry_delay" : 1, "retry_type" : "incremental_back_off", "delay_cap" : 256 },
        "content_malformed" : { "retries" : 0, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
        "validation_failed" : { "retries" : 0, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
        
        "no_retries" : { "retries": 0 },
        "none_retries" : {},
        "one_retry" : { "retries" : 1 },
        "delay_2" : { "retries" : 2, "retry_delay" : 2 },
        "example_timeout" : { "retries" : 3, "retry_delay" : 1, "retry_type" : "linear", "delay_cap" : -1 }
    },

    "cache" : {
        "max_cache_duration" : 86400
    }
}
''')

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
    """
    def __init__(self, id=None, metrics_exceptions=None, aliases_exceptions=None):
        Provider.__init__(self, None)
        self.config = base_provider_conf
        self.id = id
        self.metrics_exceptions = metrics_exceptions
        self.aliases_exceptions = aliases_exceptions
        self.metrics_processed = {}
        self.aliases_processed = {}

    def aliases(self, item):
        if self.aliases_exceptions:
            if self.aliases_exceptions.has_key(item.id):
                if len(self.aliases_exceptions[item.id]) > 0:
                    exc = self.aliases_exceptions[item.id].pop(0)
                    if exc in [ProviderClientError, ProviderServerError]:
                        raise exc('error')
                    else:
                        raise exc
        self.aliases_processed[item.id] = True
        return item

    def metrics(self, item):
        if self.metrics_exceptions:
            if self.metrics_exceptions.has_key(item.id):
                if len(self.metrics_exceptions[item.id]) > 0:
                    exc = self.metrics_exceptions[item.id].pop(0)
                    if exc in [ProviderClientError, ProviderServerError]:
                        raise exc('error')
                    else:
                        raise exc
        self.metrics_processed[item.id] = True
        return item

    def provides_metrics(self):
        return True
        
