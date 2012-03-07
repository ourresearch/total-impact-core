from totalimpact.models import Metrics, Aliases
from totalimpact.config import Configuration
from totalimpact.providers.wikipedia import Wikipedia
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.content = content
def successful_get(self, url, headers=None, timeout=None):
    f = open(XML_DOC, "r")
    return DummyResponse(200, f.read())
def get_400(self, url, headers=None, timeout=None):
    return DummyResponse(400, "")
def get_500(self, url, headers=None, timeout=None):
    return DummyResponse(500, "")

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "test.conf.json")
XML_DOC = os.path.join(CWD, "wikipedia_response.xml")

class Test_Wikipedia(unittest.TestCase):

    def setUp(self):
        print APP_CONFIG
        print XML_DOC
        self.config = Configuration(APP_CONFIG, False)
    
    def tearDown(self):
        pass
    
    def test_01_init(self):
        # first ensure that the configuration is valid
        assert len(self.config.cfg) > 0
        
        # can we get the wikipedia config file
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        assert wcfg is not None
        
        # instantiate the configuration
        wconf = Configuration(wcfg, False)
        assert len(wconf.cfg) > 0
        
        # basic init of provider
        provider = Wikipedia(wconf, self.config)
        assert provider.config is not None
        assert provider.state is not None
        
    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        # must have the three core methods
        # return NotImplementedErrors()
        assert hasattr(provider, "member_items")
        assert hasattr(provider, "aliases")
        assert hasattr(provider, "metrics")
    
    def test_03_member_items(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        self.assertRaises(NotImplementedError, provider.member_items, "")
        
    def test_04_aliases(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        self.assertRaises(NotImplementedError, provider.aliases, None)
    
    def test_05_metrics_read_content(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        # ensure that the wikipedia reader can interpret a page appropriately
        metrics = Metrics()
        f = open(XML_DOC, "r")
        provider._extract_stats(f.read(), metrics)
        assert metrics.get("mentions", 0) == 1
        
    def test_06_metrics_sleep(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        assert provider.sleep_time() == 0
        assert provider.state.sleep_time() == 0
        
    def test_07_metrics_empty_alias_and_meta(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        alias = Aliases({"bob": ["alice"]})
        metrics = provider.metrics(alias)
        
        # at this point we can check that there is no "mentions"
        # key
        assert metrics.get("mentions", None) is None
        
        # we can also check that the meta is correct
        meta = metrics.get("meta", None)
        assert meta is not None
        
        # FIXME: needs more exploration
        assert meta == provider.config.meta
        
    def test_08_metrics_http_success(self):
        Provider.http_get = successful_get
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        metrics = provider.metrics(Aliases(d))
        
        assert metrics.get("mentions", None) is not None
        
    def test_09_metrics_http_general_fail(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        metrics = provider.metrics(Aliases(d))
        
        assert metrics is None
        
    def test_10_metrics_400(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = Metrics()
        self.assertRaises(ProviderClientError, provider._get_metrics, "10.1371/journal.pcbi.1000361", metrics)
        
    def test_11_metrics_500(self):
        Provider.http_get = get_500
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = Metrics()
        self.assertRaises(ProviderServerError, provider._get_metrics, "10.1371/journal.pcbi.1000361", metrics)