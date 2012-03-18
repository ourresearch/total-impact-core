from totalimpact.models import Item, ProviderMetric, Aliases, Metrics
from totalimpact.config import Configuration
from totalimpact.providers.wikipedia import Wikipedia
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content
def successful_get(self, url, headers=None, timeout=None):
    f = open(XML_DOC, "r")
    return DummyResponse(200, f.read())
def get_400(self, url, headers=None, timeout=None):
    return DummyResponse(400, "")
def get_500(self, url, headers=None, timeout=None):
    return DummyResponse(500, "")

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases
        self.metrics = Metrics()

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "..", "test.conf.json")
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
        assert os.path.isfile(wcfg)
        
        # instantiate the configuration
        wconf = Configuration(wcfg, False)
        assert len(wconf.cfg) > 0
        
        # basic init of provider
        provider = Wikipedia(wconf, self.config)
        assert provider.config is not None
        assert provider.state is not None
        assert provider.id == wconf.id
        
    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        # must have the four core methods
        assert hasattr(provider, "member_items")
        assert hasattr(provider, "aliases")
        assert hasattr(provider, "metrics")
        assert hasattr(provider, "provides_metrics")
    
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
        metrics = ProviderMetric()
        f = open(XML_DOC, "r")
        provider._extract_stats(f.read(), metrics)
        assert metrics.value() == 1
        
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
        
        alias = Aliases(seed={"bob": ["alice"]})
        itemJustAliases = Item(aliases=alias)
        itemWithMetrics = provider.metrics(itemJustAliases)
        
        providerMetrics = itemWithMetrics.metrics.list_provider_metrics()
        assert len(providerMetrics) == 0
        
        # we can also check that the meta is correct
        meta = itemWithMetrics.metrics.meta()
        assert meta is not None
        assert "totalimpact.providers.wikipedia.Wikipedia" in meta.keys()
        assert meta["totalimpact.providers.wikipedia.Wikipedia"].keys() == ["ignore", "last_modified", "last_requested"]

    def test_08_metrics_http_success(self):
        Provider.http_get = successful_get
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        d = {"DOI" : ["10.1371/journal.pcbi.1000361"], "URL" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)
        item = provider.metrics(item)
        
        pms = item.metrics.list_provider_metrics()
        assert pms[0].value() > 0
        
    def test_09_metrics_http_general_fail(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        d = {"DOI" : ["10.1371/journal.pcbi.1000361"], "URL" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)
        item = provider.metrics(item)
        
        pms = item.metrics.list_provider_metrics()
        assert len(pms) == 0
        
    def test_10_metrics_400(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = ProviderMetric()
        self.assertRaises(ProviderClientError, provider._get_metrics, "10.1371/journal.pcbi.1000361", metrics)
        
    def test_11_metrics_500(self):
        Provider.http_get = get_500
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = os.path.join(CWD, p["config"])
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = ProviderMetric()
        self.assertRaises(ProviderServerError, provider._get_metrics, "10.1371/journal.pcbi.1000361", metrics)