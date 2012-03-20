from totalimpact.models import Metrics, Aliases
from totalimpact.config import Configuration
from totalimpact.providers.dryad import Dryad
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content
def get_html(self, url, headers=None, timeout=None):
    f = open(DRYAD_HTML, "r")
    return DummyResponse(200, f.read())
def successful_get(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())
def get_empty(self, url, headers=None, timeout=None):
    return DummyResponse(200, "")
def get_400(self, url, headers=None, timeout=None):
    return DummyResponse(400, "")
def get_500(self, url, headers=None, timeout=None):
    return DummyResponse(500, "")

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "..", "test.conf.json")
ALIAS_DOI = "10.5061/dryad.9025"
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(CWD, "sample_extract_metrics_page.html")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(CWD, "sample_extract_aliases_page.xml")
DRYAD_HTML = os.path.join(CWD, "dryad_members.html")
DOI = "10.5061/dryad.7898"

class Test_Dryad(unittest.TestCase):

    def setUp(self):
        print APP_CONFIG
        self.config = Configuration(APP_CONFIG, False)
    
    def tearDown(self):
        pass
    
    def test_01_init(self):
        # first ensure that the configuration is valid
        assert len(self.config.cfg) > 0
        
        # can we get the dryad config file
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        print dcfg
        assert os.path.isfile(dcfg)
        
        # instantiate the configuration
        dconf = Configuration(dcfg, False)
        assert len(dconf.cfg) > 0
        
        # basic init of provider
        provider = Dryad(dconf, self.config)
        assert provider.config is not None
        assert provider.state is not None
        assert provider.id == dconf.id
        
    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        # must have the four core methods
        assert hasattr(provider, "member_items")
        assert hasattr(provider, "aliases")
        assert hasattr(provider, "metrics")
        assert hasattr(provider, "provides_metrics")
    
    def test_03_crossref_doi(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        # check that the regex is set
        assert provider.crossref_rx is not None
        
        # ensure that it matches an appropriate DOI
        assert provider.crossref_rx.search(DOI) is not None
        
        # ensure that it doesn't match an inappropriate DOI
        assert provider.crossref_rx.search("11.12354/bib") is None
        
        # now make sure that the built in method gets the same results
        assert provider._is_crossref_doi(("DOI", DOI))
        assert not provider._is_crossref_doi(("DOI", "11.12354/bib"))
    
    def test_04_member_items(self):
        Provider.http_get = get_html
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        members = provider.member_items("test", "author")
        assert len(members) == 10, str(members)
        
    def test_05_aliases_read_content(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = provider._extract_aliases(f.read())
        assert len(aliases) == 2, aliases
        
        assert ("URL", u'http://hdl.handle.net/10255/dryad.7898') in aliases
        assert ("TITLE", u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides') in aliases
    
    def test_06_aliases_400(self):
        Provider.http_get = get_400
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        self.assertRaises(ProviderClientError, provider._get_aliases, DOI)
        
    def test_07_aliases_500(self):
        Provider.http_get = get_500
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        self.assertRaises(ProviderServerError, provider._get_aliases, DOI)
    
    def test_08_aliases_success(self):
        Provider.http_get = successful_get
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        # FIXME add proper tests for aliases
        #aliases = provider._get_aliases(DOI)
        #assert len(aliases) == 1, aliases
        
        #ns, id = aliases[0]
        #assert ns == "DOI"
        #assert id == ALIAS_DOI, id
    
    def test_09_aliases_empty_success(self):
        Provider.http_get = get_empty
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        # FIXME add proper tests for aliases        
        #aliases = provider._get_aliases(DOI)
        #assert len(aliases) == 1
    
    def test_10_aliases_general_fail(self):
        Provider.http_get = get_400
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        d = {"DOI" : ["10.1371/journal.pcbi.1000361"], "URL" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)
        item = provider.aliases(item)
        
        # the aliases should be unchanged
        assert item.aliases == alias
    
    def test_11_aliases_general_success(self):
        Provider.http_get = successful_get
        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        d = {"DOI" : [DOI], "URL" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)

        # FIXME fix tests for aliases
        #item = provider.aliases(item)
        
        #assert len(item.aliases.get_aliases_list(["DOI"])) == 1
        #assert len(item.aliases.get_aliases_list(["URL"])) == 1
        
        #dois = [x[1] for x in item.aliases.get_aliases_list(["DOI"])]
        #assert DOI in dois

    def test_12_provides_metrics(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)

        assert provider.provides_metrics() == True

    def test_13_show_details_url(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)

        assert provider.get_show_details_url(DOI) == "http://dx.doi.org/" + DOI
    

    def test_14_basic_extract_stats(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        ret = provider._extract_stats(f.read())
        assert len(ret) == 4, ret

    ## FIXME supposed to take an alias metric
    def test_15_metrics(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("dryad.Dryad"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Dryad(dconf, self.config)
        
        ret = provider.metrics(DOI)
        assert len(ret.str_list_provider_metrics()) == 4, len(ret.str_list_provider_metrics())

    
    """
    FIXME: these will be useful once we implement the Dryad metrics code
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
    """