from totalimpact.models import Item, MetricSnap, Aliases, Metrics
from totalimpact.config import Configuration
from totalimpact.providers.wikipedia import Wikipedia
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError, ProviderContentMalformedError, ProviderHttpError, ProviderValidationFailedError

import os, unittest, json

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content
def successful_get(self, url, headers=None, timeout=None, error_conf=None):
    f = open(XML_DOC, "r")
    return DummyResponse(200, f.read())
def get_400(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(400, "")
def get_500(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(500, "")
def exception_http_get(self, url, headers=None, timeout=None, error_conf=None):
    raise ProviderHttpError()

def extract_stats_content_malformed(self, content, metric):
    raise ProviderContentMalformedError()
def extract_stats_validation_error(self, content, metric):
    raise ProviderValidationFailedError()

def mock_snooze_or_raise(self, type, error_conf, exception, retry):
    raise exception

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases
        self.metrics = Metrics()

CWD, _ = os.path.split(__file__)

XML_DOC = os.path.join(CWD, "wikipedia_response.xml")
EMPTY_DOC = os.path.join(CWD, "wikipedia_empty_response.xml")
INCORRECT_DOC = os.path.join(CWD, "wikipedia_incorrect_response.xml")

ERROR_CONF = json.loads('''
{
    "timeout" : { "retries" : 1, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "http_error" : { "retries" : 1, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "content_malformed" : { "retries" : 1, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "rate_limit_reached" : { },
    "client_server_error" : { },
    "validation_failed" : { }
}
''')

class Test_Wikipedia(unittest.TestCase):

    def setUp(self):
        print XML_DOC
        self.config = Configuration()
        self.old_http_get = Provider.http_get
        self.old_extract_stats = Wikipedia._extract_stats
        self.old_snooze_or_raise = Provider._snooze_or_raise
    
    def tearDown(self):
        Provider.http_get = self.old_http_get
        Provider._snooze_or_raise = self.old_snooze_or_raise
        Wikipedia._extract_stats = self.old_extract_stats
    
    def test_01_init(self):
        # first ensure that the configuration is valid
        assert len(self.config.cfg) > 0
        
        # can we get the wikipedia config file
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
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
                wcfg = p["config"]
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
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        self.assertRaises(NotImplementedError, provider.member_items, "")
        
    def test_04_aliases(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        self.assertRaises(NotImplementedError, provider.aliases, None)
    
    def test_05_metrics_extract_stats(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        # ensure that the wikipedia reader can interpret a page appropriately
        metrics = MetricSnap()
        f = open(XML_DOC, "r")
        provider._extract_stats(f.read(), metrics)
        assert metrics.value() == 1
        
        # now give it something which can't be read by the internal parser
        self.assertRaises(ProviderContentMalformedError, provider._extract_stats, object, metrics)
        
        # now give it something with no results
        m = MetricSnap()
        f = open(EMPTY_DOC, "r")
        provider._extract_stats(f.read(), m)
        assert m.value() == 0
        
        # now give it an invalid document
        m = MetricSnap()
        f = open(INCORRECT_DOC, "r")
        provider._extract_stats(f.read(), m)
        assert m.value() == 0
        
    def test_06_metrics_sleep(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        assert provider.sleep_time() == 0
        assert provider.state.sleep_time() == 0
        
    def test_07_metrics_empty_alias_and_meta(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        alias = Aliases(seed={"bob": ["alice"]})
        itemJustAliases = Item(aliases=alias)
        itemWithMetrics = provider.metrics(itemJustAliases)
        
        snaps = itemWithMetrics.metrics.list_metric_snaps()
        assert len(snaps) == 0
        
        # we can also check that the update_meta is correct
        update_meta = itemWithMetrics.metrics.update_meta()
        assert update_meta is not None
        assert "wikipedia" in update_meta.keys()
        assert set(update_meta["wikipedia"].keys()) == set(["ignore", "last_modified", "last_requested"])

    def test_08_metrics_http_success(self):
        Provider.http_get = successful_get
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)
        item = provider.metrics(item)
        
        pms = item.metrics.list_metric_snaps()
        assert pms[0].value() > 0
        
        Provider.http_get = self.old_http_get
        
    def test_09_metrics_http_general_fail(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)
        item = provider.metrics(item)
        
        pms = item.metrics.list_metric_snaps()
        assert len(pms) == 0
        
        Provider.http_get = self.old_http_get
        
    def test_10_metrics_400(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        self.assertRaises(ProviderClientError, provider._get_metrics, "10.1371/journal.pcbi.1000361")
        
        Provider.http_get = self.old_http_get
        
    def test_11_metrics_500(self):
        Provider.http_get = get_500
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        self.assertRaises(ProviderServerError, provider._get_metrics, "10.1371/journal.pcbi.1000361")
        
        Provider.http_get = self.old_http_get
        
    def test_12_mitigated_get_metrics_success(self):
        Provider.http_get = successful_get
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        provider._mitigated_get_metrics("url", metrics)
        assert metrics.value() == 1
        
        Provider.http_get = self.old_http_get
        
    def test_13_mitigated_get_metrics_http_error(self):
        Provider.http_get = exception_http_get
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        self.assertRaises(ProviderHttpError, provider._mitigated_get_metrics, "url", metrics)
        
        Provider.http_get = self.old_http_get
    
    def test_14_mitigated_get_metrics_client_server_errors(self):
        Provider.http_get = get_400
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        self.assertRaises(ProviderClientError, provider._mitigated_get_metrics, "url", metrics)
        
        Provider.http_get = get_500
        
        metrics = MetricSnap()
        self.assertRaises(ProviderServerError, provider._mitigated_get_metrics, "url", metrics)
        
        Provider.http_get = self.old_http_get
    
    def test_15_mitigated_get_metrics_content_malformed(self):
        Provider.http_get = successful_get
        Provider._snooze_or_raise = mock_snooze_or_raise
        Wikipedia._extract_stats = extract_stats_content_malformed
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        self.assertRaises(ProviderContentMalformedError, provider._mitigated_get_metrics, "url", metrics)
        
        Provider.http_get = self.old_http_get
        Wikipedia._extract_stats = self.old_extract_stats
        Provider._snooze_or_raise = self.old_snooze_or_raise
        
    def test_16_mitigated_get_metrics_validation_failed(self):
        Provider.http_get = successful_get
        Provider._snooze_or_raise = mock_snooze_or_raise
        Wikipedia._extract_stats = extract_stats_validation_error
        
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf, self.config)
        
        metrics = MetricSnap()
        self.assertRaises(ProviderValidationFailedError, provider._mitigated_get_metrics, "url", metrics)
        
        Provider.http_get = self.old_http_get
        Wikipedia._extract_stats = self.old_extract_stats
        Provider._snooze_or_raise = self.old_snooze_or_raise