import requests, os, unittest
from totalimpact.providers.provider import Provider, ProviderFactory, ProviderHttpError, ProviderTimeout
from totalimpact.config import Configuration

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "test.conf.json")

def successful_get(url, headers=None, timeout=None):
    return url
def timeout_get(url, headers=None, timeout=None):
    raise requests.exceptions.Timeout()
def error_get(url, headers=None, timeout=None):
    raise requests.exceptions.RequestException()

class Test_Provider(unittest.TestCase):

    def setUp(self):
        print APP_CONFIG
        self.config = Configuration(APP_CONFIG, False)
    
    def tearDown(self):
        pass
    
    def test_01_init(self):
        # since the provider is really abstract, this doen't
        # make much sense, but we do it anyway
        # anyway
        provider = Provider(None, self.config)

    def test_02_interface(self):
        # check that the interface is defined, and has appropriate
        # defaults/NotImplementedErrors
        provider = Provider(None, self.config)
        
        assert not provider.provides_metrics()
        self.assertRaises(NotImplementedError, provider.member_items, None, None)
        self.assertRaises(NotImplementedError, provider.aliases, None)
        self.assertRaises(NotImplementedError, provider.metrics, None)
        
    def test_03_error(self):
        # FIXME: will need to test this when the error handling is written
        pass
        
    def test_04_sleep(self):
        provider = Provider(None, self.config)
        assert provider.sleep_time() == 0
        
    def test_05_request_error(self):
        requests.get = error_get
        
        provider = Provider(None, self.config)
        self.assertRaises(ProviderHttpError, provider.http_get, "", None, None)
        
    def test_06_request_error(self):
        requests.get = timeout_get
        
        provider = Provider(None, self.config)
        self.assertRaises(ProviderTimeout, provider.http_get, "", None, None)
        
    def test_07_request_error(self):
        requests.get = successful_get
        
        provider = Provider(None, self.config)
        r = provider.http_get("test")
        
        assert r == "test"
        
    # FIXME: we will also need tests to cover the cacheing when that
    # has been implemented
    
    def test_08_get_provider(self):
        pconf = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                pconf = p
                break
        provider = ProviderFactory.get_provider(pconf, self.config)
        assert provider.id == "Wikipedia:mentions"
        
    def test_09_get_providers(self):
        providers = ProviderFactory.get_providers(self.config)
        assert len(providers) == len(self.config.providers)
