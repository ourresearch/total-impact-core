import requests, os, unittest, time, threading, json, memcache, sys, traceback
from test.utils import slow

from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.providers.provider import ProviderError, ProviderTimeout, ProviderServerError
from totalimpact.providers.provider import ProviderClientError, ProviderHttpError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderConfigurationError, ProviderValidationFailedError
from totalimpact.cache import Cache
from totalimpact import api
from nose.tools import assert_equals

CWD, _ = os.path.split(__file__)

def successful_get(url, headers=None, timeout=None):
    return url
def timeout_get(url, headers=None, timeout=None):
    raise requests.exceptions.Timeout()
def error_get(url, headers=None, timeout=None):
    raise requests.exceptions.RequestException()

def mock_get_cache_entry(self, url):
    return None
def mock_set_cache_entry_null(self, url, data):
    pass

class InterruptableSleepThread(threading.Thread):
    def run(self):
        provider = Provider(None)
        provider._interruptable_sleep(0.5)
    
    def _interruptable_sleep(self, snooze, duration):
        time.sleep(0.5)

class InterruptableSleepThread2(threading.Thread):
    def __init__(self, method, *args):
        super(InterruptableSleepThread2, self).__init__()
        self.method = method
        self.args = args
        self.failed = False
        self.exception = None
        
    def run(self):
        try:
            self.method(*self.args)
        except Exception as e:
            self.failed = True
            self.exception = e
    
    def _interruptable_sleep(self, snooze, duration):
        time.sleep(snooze)


class Test_Provider(unittest.TestCase):

    def setUp(self):
        self.old_http_get = requests.get
        self.old_get_cache_entry = Cache.get_cache_entry
        self.old_set_cache_entry = Cache.set_cache_entry
        
        Cache.get_cache_entry = mock_get_cache_entry
        Cache.set_cache_entry = mock_set_cache_entry_null
        
        # FIXME: this belongs in a cache testing class, rather than here
        # in this unit we'll just mock out the cache
        #
        # Clear memcache so we have an empty cache for testing
        #mc = memcache.Client(['127.0.0.1:11211'])
        #mc.flush_all()
        
        # Create a base config which provides necessary settings
        # which all providers should at least implement
        self.provider_configs = api.app.config["PROVIDERS"]
    
    def tearDown(self):
        requests.get = self.old_http_get
        Cache.get_cache_entry = self.old_get_cache_entry
        Cache.set_cache_entry = self.old_set_cache_entry
        
        # FIXME: this belongs in a cache testing class, rather than here
        # in this unit we'll just mock out the cache
        #
        # Clear memcache in case we have stored anything
        #mc = memcache.Client(['127.0.0.1:11211'])
        #mc.flush_all()
        
    # FIXME: we will also need tests to cover the cacheing when that
    # has been implemented
    
    def test_08_get_provider(self):
        provider = ProviderFactory.get_provider("wikipedia")
        assert_equals(provider.__class__.__name__, "Wikipedia")
        
    def test_09_get_providers(self):
        providers = ProviderFactory.get_providers(self.provider_configs)
        assert len(providers) == len(self.provider_configs)
        pass


    
        
