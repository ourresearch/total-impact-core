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
      
    @slow    
    def test_06_sleep_interrupt(self):
        st = StoppableThread()
        
        # basic interruptable sleep
        start = time.time()
        st._interruptable_sleep(2*TIME_SCALE)
        took = time.time() - start
        assert took < 2*TIME_SCALE+0.1, took # take into account interval on interruptable sleep
        
        # advanced interruptable sleep
        start = time.time()
        st._interruptable_sleep(3*TIME_SCALE, 0.1)
        took = time.time() - start
        assert took < 3*TIME_SCALE+0.1, took
        
        # now try interrupting the sleep (need to use a special wrapper
        # class defined above to get this done)
        start = time.time()
        InterruptTester().run(2*TIME_SCALE)
        took = time.time() - start
        assert took < 2*BACKEND_POLL_INTERVAL+0.1, took # taking into account all the sleep delays
        
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
        
    @slow    
    def test_10_alias_running(self):
        # relies on Queue.first mock as per setUp
        providers = [ProviderMock()]
        pat = ProvidersAliasThread(providers, self.config)
        pat.queue = QueueMock()
        
        start = time.time()
        pat.start()
        time.sleep(2*TIME_SCALE)
        
        pat.stop()
        pat.join()
        took = time.time() - start
        
        # there are no assertions to make here, only that the
        # test completes without error in the appropriate time
        assert took > 2*TIME_SCALE, took
        assert took < 2*BACKEND_POLL_INTERVAL+0.1, took

    @slow
    def test_11_alias_provider_not_implemented(self):
        # relies on Queue.first mock as per setUp
        
        providers = [ProviderNotImplemented()] 
        pat = ProvidersAliasThread(providers, self.d)
        pat.queue = QueueMock()
        
        start = time.time()
        pat.start()
        time.sleep(2*TIME_SCALE)
        
        pat.stop()
        pat.join()
        took = time.time() - start
        
        # The NotImplementedErrors should not derail the thread
        assert took > 2*TIME_SCALE, took
        assert took < 2*BACKEND_POLL_INTERVAL+0.1, took
        
        
    # FIXME: save_and_unqueue is not yet working, so will need more
    # tests when it is
    
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
        
    @slow    
    def test_13_metrics_running(self):
        # relies on Queue.first mock as per setUp
        pmt = ProviderMetricsThread(ProviderMock(), self.d)
        pmt.queue = QueueMock()
        
        start = time.time()
        pmt.start()
        time.sleep(2*TIME_SCALE)
        
        pmt.stop()
        pmt.join()
        took = time.time() - start
        
        # there are no assertions to make here, only that the
        # test completes without error in the appropriate time
        assert took > 2*TIME_SCALE, took
        assert took < 2*BACKEND_POLL_INTERVAL+0.1, took
        
    @slow
    @nottest
    def test_14_backend(self):
        watcher = TotalImpactBackend(self.d, self.providers)

        watcher._spawn_threads()
        assert len(watcher.threads) >= len(self.providers)+2, len(watcher.threads)
       
        watcher._cleanup()
        assert len(watcher.threads) == 0, len(watcher.threads)

    @slow
    def test_16_metrics_retries(self):
        """ test_16_metrics_retries
 
            Check that we are doing the correct behaviour for retries.
            Retries for rate limits should go forever, with exponential falloff
            Exceeding retry limit should result in a failure
        """
        mock_provider = ProviderMock(
            metrics_exceptions={
                1:[ProviderRateLimitError,ProviderRateLimitError,ProviderRateLimitError],
                2:[ProviderTimeout,ProviderTimeout,ProviderTimeout,ProviderTimeout, ProviderTimeout, ProviderTimeout],
            }
        ) 
        pmt = ProviderMetricsThread(mock_provider, self.d)
        pmt.queue = QueueMock(max_items=2)
        
        start = time.time()
        pmt.start()
        while (pmt.queue.current_item <= 2): 
            time.sleep(1*TIME_SCALE)
        took = time.time() - start
        pmt.stop()
        pmt.join()

        # Total time should be 3 * exponential backoff, and 3 * constant (linear) delay
        assert took >= ((1 + 2 + 4) + (0.1 * 3)), took
        # Check that item 1 was processed correctly, after retries
        assert mock_provider.metrics_processed.has_key(1)
        # Check that item 2 did not get processed as it exceeded the failure limit
        ## FIXME re-enable this test after queue refactor in sprint 6        
        ## self.assertFalse(mock_provider.metrics_processed.has_key(2))

    @slow
    def test_17_alias_thread(self):
        """ test_17_alias_thread

            Set up the ProvidersAliasThread with a single mock provider. Check
            that it runs successfully with a single item in the queue, and that
            it processes the item ok.
        """
        mock_provider = ProviderMock() 
        pmt = ProvidersAliasThread([mock_provider], self.d)
        pmt.queue = QueueMock(max_items=1)
        
        pmt.start()
        while (pmt.queue.current_item <= 1): 
            time.sleep(20*TIME_SCALE)
        pmt.stop()
        pmt.join()

        # Check that item 1 was processed correctly, after a retry
        assert mock_provider.aliases_processed.has_key(1)

 