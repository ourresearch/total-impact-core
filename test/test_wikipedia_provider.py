from unittest import TestCase
import totalimpact

#from totalimpact.config import Configuration
#from totalimpact.providers.wikipedia import Wikipedia

class WikipediaTest(TestCase):

    def setUp(self):
        super(WikipediaTest, self).setUp()
        #self.config = Configuration("test/test.conf.json", False)
    
    def tearDown(self):
        super(WikipediaTest, self).tearDown()

    def test_01_init(self):
        print dir(totalimpact)
        # first ensure that the configuration is valid
        assert len(self.config.cfg) > 0
        
        # can we get the wikipedia config file
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        assert wcfg is not None
        
        # instantiate the configuration
        wconf = Configuration(wcfg, False)
        assert len(wconf.cfg) > 0
        
        # basic init of provider
        provider = Wikipedia(wconf)
        assert provider.config is not None
        
    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf)
        
        # must have the three core methods
        # return NotImplementedErrors()
        assert hasattr(provider, "member_items")
        assert hasattr(provider, "aliases")
        assert hasattr(provider, "metrics")
    
    def test_03_member_items(self):
        pass
        
    def test_04_aliases(self):
        pass
    
    """
    def test_05_metrics(self):
        wcfg = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                wcfg = p["config"]
        wconf = Configuration(wcfg, False)
        provider = Wikipedia(wconf)
        
        # ensure that the wikipedia reader can interpret a page appropriately
        metrics = Metrics()
        f = open("wikipedia_response.xml")
        provider._extract_stats(f.read(), metrics)
        assert metrics.get("mentions", 0) == 1
        
        # ensure that the metric is as we would expect
        # FIXME: we need to mock out the http layer to do this
    """
