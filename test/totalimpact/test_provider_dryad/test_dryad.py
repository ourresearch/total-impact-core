from totalimpact.models import Metrics, Aliases
from totalimpact.config import Configuration
from totalimpact.providers.dryad import Dryad
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest
from nose.tools import nottest, raises

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content

def get_member_items_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_member_items_html_zero_items(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS, "r")
    return DummyResponse(200, f.read())

def get_aliases_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())

def get_nonsense_xml(self, url, headers=None, timeout=None):
    return DummyResponse(200, '<?xml version="1.0" encoding="UTF-8"?><nothingtoseehere>nonsense</nothingtoseehere>')

def get_nonsense_txt(self, url, headers=None, timeout=None):
    return DummyResponse(200, "nonsense")

def get_empty(self, url, headers=None, timeout=None):
    return DummyResponse(200, "")

def get_400(self, url, headers=None, timeout=None):
    return DummyResponse(400, "")

def get_500(self, url, headers=None, timeout=None):
    return DummyResponse(500, "")


CWD, _ = os.path.split(__file__)

DRYAD_CONFIG_FILENAME = "totalimpact/providers/dryad.conf.json"
TEST_DRYAD_DOI = "10.5061/dryad.7898"
TEST_DRYAD_AUTHOR = "Piwowar, Heather A."
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(CWD, "sample_extract_metrics_page.html")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(CWD, "sample_extract_aliases_page.xml")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(CWD, "sample_extract_member_items_page.xml")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS = os.path.join(CWD, "sample_extract_member_items_page_zero_items.xml")

class Test_Dryad(unittest.TestCase):

    def setUp(self):
        self.old_http_get = Provider.http_get
        self.config = Configuration(DRYAD_CONFIG_FILENAME, False)
        self.provider = Dryad(self.config)

    
    def tearDown(self):
        Provider.http_get = self.old_http_get
    

    def test_01_init(self):
        # ensure that the configuration is valid
        assert self.provider.config is not None
        assert self.provider.state is not None
        assert self.provider.id == "Dryad"
        

    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        # must have the four core methods
        assert hasattr(self.provider, "member_items")
        assert hasattr(self.provider, "aliases")
        assert hasattr(self.provider, "metrics")
        assert hasattr(self.provider, "provides_metrics")
    

    def test_03_is_relevant_id(self):
        # ensure that it matches an appropriate TEST_DRYAD_DOI
        assert not self.provider._is_relevant_id("11.12354/bib")
        
        # ensure that it doesn't match an inappropriate TEST_DRYAD_DOI
        assert not self.provider._is_relevant_id(("DOI", "11.12354/bib"))
    

    def test_04a_member_items_success(self):
        Provider.http_get = get_member_items_html_success
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 4, str(members)

    def test_04f_member_items_zero_items(self):
        Provider.http_get = get_member_items_html_zero_items
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 0, str(members)

    @raises(ProviderClientError)
    def test_04b_member_items_400(self):
        Provider.http_get = get_400
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")

    @raises(ProviderServerError)
    def test_04c_member_items_500(self):
        Provider.http_get = get_500
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")

    @raises(ProviderClientError)
    def test_04d_member_items_empty(self):
        Provider.http_get = get_empty
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")

    @raises(ProviderClientError)
    def test_04g_member_items_nonsense_txt(self):
        Provider.http_get = get_nonsense_txt
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 0, str(members)

    @raises(ProviderClientError)
    def test_04h_member_items_nonsense_xml(self):
        Provider.http_get = get_nonsense_xml
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 0, str(members)

        
    def test_05_aliases_read_content(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = self.provider._extract_aliases(f.read())
        assert len(aliases) == 2, aliases
        
        assert ("URL", u'http://hdl.handle.net/10255/dryad.7898') in aliases
        assert ("TITLE", u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides') in aliases
    
    def test_06_aliases_400(self):
        Provider.http_get = get_400
        self.assertRaises(ProviderClientError, self.provider._get_aliases, TEST_DRYAD_DOI)
        
    def test_07_aliases_500(self):
        Provider.http_get = get_500
        self.assertRaises(ProviderServerError, self.provider._get_aliases, TEST_DRYAD_DOI)
    
    def test_08_aliases_success(self):
        Provider.http_get = get_aliases_html_success
        
        # FIXME add proper tests for aliases
        #aliases = provider._get_aliases(TEST_DRYAD_DOI)
        #assert len(aliases) == 1, aliases
        
        #ns, id = aliases[0]
        #assert ns == "DOI"
        #assert id == ALIAS_DOI, id
    
    def test_09_aliases_empty_success(self):
        Provider.http_get = get_empty
        
        # FIXME add proper tests for aliases        
        #aliases = provider._get_aliases(TEST_DRYAD_DOI)
        #assert len(aliases) == 1
    
    def test_10_aliases_general_fail(self):
        Provider.http_get = get_400
        
        d = {"DOI" : ["10.1371/journal.pcbi.1000361"], "URL" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)
        item = self.provider.aliases(item)
        
        # the aliases should be unchanged
        assert item.aliases == alias
    
    def test_11_aliases_general_success(self):
        Provider.http_get = get_aliases_html_success
        
        d = {"DOI" : [TEST_DRYAD_DOI], "URL" : ["http://cottagelabs.com"]}
        alias = Aliases(seed=d)
        item = Item(aliases=alias)

        # FIXME fix tests for aliases
        #item = provider.aliases(item)
        
        #assert len(item.aliases.get_aliases_list(["DOI"])) == 1
        #assert len(item.aliases.get_aliases_list(["URL"])) == 1
        
        #dois = [x[1] for x in item.aliases.get_aliases_list(["DOI"])]
        #assert TEST_DRYAD_DOI in dois

    @nottest
    def test_12_provides_metrics(self):
        assert self.provider.provides_metrics() == True


    def test_13_show_details_url(self):
        assert self.provider.get_show_details_url(TEST_DRYAD_DOI) == "http://dx.doi.org/" + TEST_DRYAD_DOI
    

    def test_14_basic_extract_stats(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        ret = self.provider._extract_stats(f.read())
        assert len(ret) == 4, ret

    @nottest
    ## FIXME supposed to take an alias metric
    def test_15_metrics(self):
        ret = self.provider.metrics(TEST_DRYAD_DOI)
        assert len(ret.str_list_provider_metrics()) == 4, len(ret.str_list_provider_metrics())

    
    """
    FIXME: these will be useful once we implement the Dryad metrics code
    def test_05_metrics_read_content(self):
        # ensure that the wikipedia reader can interpret a page appropriately
        metrics = Metrics()
        f = open(XML_DOC, "r")
        provider._extract_stats(f.read(), metrics)
        assert metrics.get("mentions", 0) == 1
        
    def test_06_metrics_sleep(self):      
        assert provider.sleep_time() == 0
        assert provider.state.sleep_time() == 0
        
    def test_07_metrics_empty_alias_and_meta(self):
        alias = Aliases({"bob": ["alice"]})
        metrics = provider.metrics(alias)
        
        # at this point we can check that there is no "mentions" key
        assert metrics.get("mentions", None) is None
        
        # we can also check that the meta is correct
        meta = metrics.get("meta", None)
        assert meta is not None
        
        # FIXME: needs more exploration
        assert meta == provider.config.meta
        
    def test_08_metrics_http_success(self):
        Provider.http_get = successful_get
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        metrics = provider.metrics(Aliases(d))
        
        assert metrics.get("mentions", None) is not None
        
    def test_09_metrics_http_general_fail(self):
        Provider.http_get = get_400
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        metrics = provider.metrics(Aliases(d))
        
        assert metrics is None
        
    def test_10_metrics_400(self):
        Provider.http_get = get_400
        metrics = Metrics()
        self.assertRaises(ProviderClientError, provider._get_metrics, "10.1371/journal.pcbi.1000361", metrics)
        
    def test_11_metrics_500(self):
        Provider.http_get = get_500
        metrics = Metrics()
        self.assertRaises(ProviderServerError, provider._get_metrics, "10.1371/journal.pcbi.1000361", metrics)
    """