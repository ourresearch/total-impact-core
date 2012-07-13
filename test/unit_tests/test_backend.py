import os, unittest, time, logging
from nose.tools import nottest, assert_equals
from test.utils import slow

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact import dao

# To read global config
from totalimpact import app

TEST_DB_NAME = "test_dao"

from totalimpact.providers.provider import ProviderTimeout, ProviderRateLimitError

from test.mocks import ProviderMock, QueueMock, ItemMock

def slow(f):
    f.slow = True
    return f

logging.disable(logging.CRITICAL)
CWD, _ = os.path.split(__file__)

TIME_SCALE = 0.0005 #multiplier to run the tests as fast as possible
BACKEND_POLL_INTERVAL = 0.5 #seconds

def dao_init_mock(self, name, url):
    pass

class InterruptTester(object):
    def run(self, stop_after=0):
        st = StoppableThread()
        st.start()
        
        time.sleep(stop_after)
        st.stop()
        st.join()

class ProviderNotImplemented(Provider):
    def __init__(self):
        Provider.__init__(self, None)
        self.provider_name = 'not_implemented'
    def aliases(self, item, provider_url_template=None, cache_enabled=True):
        raise NotImplementedError()
    def metrics(self, item, provider_url_template=None, cache_enabled=True):
        raise NotImplementedError()

def first_mock(self):
    return ItemMock()
def save_and_unqueue_mock(self, item):
    pass
    
def get_providers_mock(cls, config):
    return [ProviderMock("1"), ProviderMock("2"), ProviderMock("3")]



class TestBackend():
    
    def setUp(self):
        self.config = None #placeholder
        TEST_PROVIDER_CONFIG = [
            ("wikipedia", {})
        ]
        self.d = dao.Dao(os.environ["CLOUDANT_URL"], os.environ["CLOUDANT_DB"])

        self.get_providers = ProviderFactory.get_providers
        ProviderFactory.get_providers = classmethod(get_providers_mock)

        self.providers = self.get_providers(TEST_PROVIDER_CONFIG)
        
        
    def teardown(self):
        # FIXME: check that this doesn't need to be wrapped in a classmethod() call
        ProviderFactory.get_providers = self.get_providers
        self.d.delete_db(os.environ["CLOUDANT_DB"])

    def test_01_init_backend(self):
        watcher = TotalImpactBackend(self.d, self.providers)
        
        assert len(watcher.threads) == 0
        assert len(watcher.providers) == len(self.providers), len(watcher.providers)
        
        
    def test_05_run_stop(self):
        st = StoppableThread()
        assert not st.stopped()
        
        st.stop()
        assert st.stopped()
   
    def test_09_alias_stopped(self):
        # relies on Queue.first mock as per setUp
        
        providers = [ProviderMock()]
        pat = ProvidersAliasThread(providers, self.config)
        pat.queue = QueueMock()
        
        pat.start()
        pat.stop()
        pat.join()
        
        # there are no assertions to make here, only that the
        # test completes without error
        assert True
       
    def test_12_metrics_stopped(self):
        # relies on Queue.first mock as per setUp
        pmt = ProviderMetricsThread(ProviderMock(), self.d)
        pmt.queue = QueueMock()
        
        pmt.start()
        pmt.stop()
        pmt.join()
        
        # there are no assertions to make here, only that the
        # test completes without error
        assert True
        
 

 
