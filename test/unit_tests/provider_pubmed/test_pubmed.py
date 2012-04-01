from totalimpact.models import Metrics, Aliases
from totalimpact.config import Configuration
from totalimpact.providers.pubmed import Pubmed
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content

def get_memberitems_html(self, url, headers=None, timeout=None):
    f = open(PUBMED_MEMBERITEMS_HTML, "r")
    return DummyResponse(200, f.read())

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases

CWD, _ = os.path.split(__file__)

PUBMED_MEMBERITEMS_HTML = os.path.join(CWD, "sample_pubmed_memberitems.xml")
DOI = "10.5061/dryad.7898"

class Test_Pubmed(unittest.TestCase):

    def setUp(self):
        self.config = Configuration()
        self.old_http_get = Provider.http_get
    
    def tearDown(self):
        Provider.http_get = self.old_http_get
    
    def test_01_init(self):
        # first ensure that the configuration is valid
        assert len(self.config.cfg) > 0
        
        # can we get the config file
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("pubmed.Pubmed"):
                dcfg = p["config"]
        print dcfg
        assert os.path.isfile(dcfg)
        
        # instantiate the configuration
        dconf = Configuration(dcfg, False)
        assert len(dconf.cfg) > 0
        
        # basic init of provider
        provider = Pubmed(dconf, self.config)
        assert provider.config is not None

        ## FIXME implement state
        #assert provider.state is not None

        assert provider.id == dconf.id
        
    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("pubmed.Pubmed"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Pubmed(dconf, self.config)
        
        # must have the four core methods
        assert hasattr(provider, "member_items")
        assert hasattr(provider, "aliases")
        assert hasattr(provider, "metrics")
        assert hasattr(provider, "provides_metrics")
    

    def test_04_member_items(self):
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("pubmed.Pubmed"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Pubmed(dconf, self.config)
        
        Provider.http_get = get_memberitems_html

        members = provider.member_items("U54-CA121852", "pubmedGrant")
        assert len(members) >= 20, len(members)
        
