import os, unittest
from totalimpact.watchers import Watchers, ProviderMetricsThread, ProvidersAliasThread
from totalimpact.config import Configuration
from totalimpact.providers.provider import Provider, ProviderFactory

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "test.conf.json")

class Test_Watchers(unittest.TestCase):

    def setUp(self):
        print APP_CONFIG
        self.config = Configuration(APP_CONFIG, False)
    
    def tearDown(self):
        pass
    
    def test_01_init_watcher(self):
        watcher = Watchers(APP_CONFIG)
        
        assert len(watcher.threads) == 0
        assert watcher.config is not None
        assert len(watcher.providers) == 4
        
    def test_02_init_metrics(self):
        provider = Provider(None, self.config)
        provider.id = "test"
        pmt = ProviderMetricsThread(provider, self.config)
        
        assert hasattr(pmt, "stop")
        assert hasattr(pmt, "stopped")
        assert hasattr(pmt, "first")
        assert pmt.queue is not None
        assert pmt.provider.id == "test"
        assert pmt.config is not None
        assert pmt.queue.provider == "test"
        
    def test_03_init_aliases(self):
        providers = ProviderFactory.get_providers(self.config)
        pat = ProvidersAliasThread(providers, self.config)
        
        assert hasattr(pat, "stop")
        assert hasattr(pat, "stopped")
        assert hasattr(pat, "first")
        assert pat.config is not None
        assert pat.queue is not None
        
    def test_04_alias_sleep(self):
        providers = ProviderFactory.get_providers(self.config)
        pat = ProvidersAliasThread(providers, self.config)
        assert pat.sleep_time() == 0
        
    