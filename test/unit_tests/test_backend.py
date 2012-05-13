import os, unittest, time
from nose.tools import nottest, assert_equals
from test.utils import slow

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
from totalimpact import dao, api
from totalimpact.tilogging import logging

# To read global config
from totalimpact.api import app

TEST_DB_NAME = "test_dao"

from totalimpact.providers.provider import ProviderConfigurationError, ProviderTimeout, ProviderHttpError
from totalimpact.providers.provider import ProviderClientError, ProviderServerError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderValidationFailedError, ProviderRateLimitError

from test.mocks import ProviderMock, QueueMock, ItemMock

def slow(f):
    f.slow = True
    return f

logger = logging.getLogger(__name__)
CWD, _ = os.path.split(__file__)

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
    def aliases(self, item):
        raise NotImplementedError()
    def metrics(self, item):
        raise NotImplementedError()

def first_mock(self):
    return ItemMock()
def save_and_unqueue_mock(self, item):
    pass
    
def get_providers_mock(cls, config):
    return [ProviderMock("1"), ProviderMock("2"), ProviderMock("3")]



class TestBackend(unittest.TestCase):
    
    def setUp(self):
        self.config = None #placeholder

        TEST_DB_NAME = "test_backend"
        TEST_PROVIDER_CONFIG = {
            "wikipedia": {}
        }

        self.d = dao.Dao(TEST_DB_NAME, app.config["DB_URL"],
            app.config["DB_USERNAME"], app.config["DB_PASSWORD"])
        self.d.create_new_db_and_connect(TEST_DB_NAME)

        self.get_providers = ProviderFactory.get_providers
        ProviderFactory.get_providers = classmethod(get_providers_mock)

        self.providers = self.get_providers(TEST_PROVIDER_CONFIG)
        
        
    def tearDown(self):
        # FIXME: check that this doesn't need to be wrapped in a classmethod() call
        ProviderFactory.get_providers = self.get_providers

    def test_01_init_backend(self):
        watcher = TotalImpactBackend(self.d, self.providers)
        
        assert len(watcher.threads) == 0
        assert len(watcher.providers) == len(self.providers), len(watcher.providers)
        
    def test_02_init_metrics(self):
        provider = Provider(None)
        provider.provider_name = "test"
        pmt = ProviderMetricsThread(provider, self.d)
        
        assert hasattr(pmt, "stop")
        assert hasattr(pmt, "stopped")
        assert hasattr(pmt, "first")
        assert pmt.queue is not None
        assert pmt.provider.provider_name == "test"
        assert pmt.queue.provider == "test"
        
    def test_03_init_aliases(self):
        providers = ProviderFactory.get_providers(self.config)
        pat = ProvidersAliasThread(providers, self.d)
        
        assert hasattr(pat, "stop")
        assert hasattr(pat, "stopped")
        assert hasattr(pat, "first")
        assert pat.queue is not None
        
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
        st._interruptable_sleep(2)
        took = time.time() - start
        assert took < 2.6 # take into account interval on interruptable sleep
        
        # advanced interruptable sleep
        start = time.time()
        st._interruptable_sleep(3, 0.1)
        took = time.time() - start
        assert took < 4.3, took
        
        # now try interrupting the sleep (need to use a special wrapper
        # class defined above to get this done)
        start = time.time()
        InterruptTester().run(2)
        took = time.time() - start
        assert took < 3 # taking into account all the sleep delays

    @slow
    def test_07_queue_consumer(self):
        q = QueueConsumer(QueueMock())
        
        # the QueueMock will return None 3 times before giving
        # an item, so this operation should take more than 1.5
        # seconds
        start = time.time()
        item = q.first()
        took = time.time() - start
        assert took > 1.5, took
        assert took < 2.0, took
        
    def test_08_stopped_queue(self):
        q = QueueConsumer(QueueMock())
        q.stop()
        item = q.first()
        assert item is None
        
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
        time.sleep(2)
        
        pat.stop()
        pat.join()
        took = time.time() - start
        
        # there are no assertions to make here, only that the
        # test completes without error in the appropriate time
        assert took > 2.0
        assert took < 2.5

    @slow
    def test_11_alias_provider_not_implemented(self):
        # relies on Queue.first mock as per setUp
        
        providers = [ProviderNotImplemented()] 
        pat = ProvidersAliasThread(providers, self.d)
        pat.queue = QueueMock()
        
        start = time.time()
        pat.start()
        time.sleep(2)
        
        pat.stop()
        pat.join()
        took = time.time() - start
        
        # The NotImplementedErrors should not derail the thread
        assert took > 2.0
        assert took < 2.5
        
        
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
        time.sleep(2)
        
        pmt.stop()
        pmt.join()
        took = time.time() - start
        
        # there are no assertions to make here, only that the
        # test completes without error in the appropriate time
        assert took > 2.0
        assert took < 2.5
        
    # FIXME: save_and_unqueue is not yet working, so will need more
    # tests when it is
    @slow
    def test_14_backend(self):
        watcher = TotalImpactBackend(self.d, self.providers)
        
        watcher._spawn_threads()
        assert len(watcher.threads) == len(self.providers)+1, len(watcher.threads)
        
        watcher._cleanup()
        assert len(watcher.threads) == 0, len(watcher.threads)

    @slow
    def test_15_metrics_exceptions(self):
        """ test_15_metrics_exceptions

            Check exceptions raised by the metric function on providers
            This test ensures that we generate and handle each exception
            type possible from the providers.
        """
        mock_provider = ProviderMock(
            metrics_exceptions={
                1:[ProviderTimeout,ProviderTimeout],
                2:[ProviderHttpError],
                3:[ProviderClientError],
                4:[ProviderServerError],
                5:[ProviderTimeout,ProviderRateLimitError],
                6:[ProviderContentMalformedError],
                7:[ProviderValidationFailedError],
                8:[ProviderConfigurationError],
                9:[Exception],
            }
        ) 
        pmt = ProviderMetricsThread(mock_provider, self.config)
        pmt.queue = QueueMock(max_items=10)
        
        pmt.start()
        while (pmt.queue.current_item <= 10): 
            time.sleep(1)
    
        pmt.stop()
        pmt.join()

        # Check that items 1,2 were all processed correctly, after a retry
        self.assertTrue(mock_provider.metrics_processed.has_key(1))
        self.assertTrue(mock_provider.metrics_processed.has_key(2))
    
        # Check that item 9 did not get processed as it had a permanent failure
        self.assertFalse(mock_provider.metrics_processed.has_key(9))

        # Check that item 10 was processed correctly 
        self.assertTrue(mock_provider.metrics_processed.has_key(10))

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
        pmt = ProviderMetricsThread(mock_provider, self.config)
        pmt.queue = QueueMock(max_items=2)
        
        start = time.time()
        pmt.start()
        while (pmt.queue.current_item <= 2): 
            time.sleep(1)
        took = time.time() - start
        pmt.stop()
        pmt.join()

        # Total time should be 3 * exponential backoff, and 3 * constant (linear) delay
        assert took >= (1 + 2 + 4) + (0.1 * 3), took
        # Check that item 1 was processed correctly, after retries
        self.assertTrue(mock_provider.metrics_processed.has_key(1))
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
        pmt = ProvidersAliasThread([mock_provider], self.config)
        pmt.queue = QueueMock(max_items=1)
        
        pmt.start()
        while (pmt.queue.current_item <= 1): 
            time.sleep(1)
        pmt.stop()
        pmt.join()

        # Check that item 1 was processed correctly, after a retry
        self.assertTrue(mock_provider.aliases_processed.has_key(1))

    @slow
    def test_18_alias_exceptions(self):
        """ test_18_alias_exceptions

            Set up the ProvidersAliasThread with a two mock providers, which 
            simulate errors on processing aliases for various items. Check that
            we handle retries correctly.
        """
        mock_provider1 = ProviderMock(
            aliases_exceptions={
                1:[ProviderRateLimitError,ProviderRateLimitError,ProviderRateLimitError],
                2:[ProviderTimeout,ProviderTimeout,ProviderTimeout,ProviderTimeout],
                4:[ProviderTimeout],
            }
        )
        mock_provider1.name = 'mock1'

        mock_provider2 = ProviderMock(
            aliases_exceptions={
                1:[ProviderRateLimitError,ProviderRateLimitError,ProviderRateLimitError],
                3:[ProviderTimeout,ProviderTimeout,ProviderTimeout,ProviderTimeout],
                4:[ProviderTimeout],
            }
        )
        mock_provider2.name = 'mock2'

        pmt = ProvidersAliasThread([mock_provider1,mock_provider2], self.config)
        pmt.queue = QueueMock(max_items=4)
        
        pmt.start()
        while (pmt.queue.current_item <= 4): 
            time.sleep(1)
        pmt.stop()
        pmt.join()

        # Check that item 1 was processed correctly, after a retry
        self.assertTrue(mock_provider1.aliases_processed.has_key(1))
        self.assertTrue(mock_provider2.aliases_processed.has_key(1))
        ns_list = [k for (k,v) in pmt.queue.items[1].aliases.get_aliases_list()]
        self.assertEqual(set(ns_list),set(['mock','doi']))

        # Check that item 2 failed on the first provider
        ## FIXME re-enable this test after queue refactor in sprint 6        
        ## self.assertFalse(mock_provider1.aliases_processed.has_key(2))
        ## self.assertFalse(mock_provider2.aliases_processed.has_key(2))
        ## self.assertEqual(pmt.queue.items[2].aliases.get_aliases_list(),[])

        # Check that item 3 failed on the second provider
        self.assertTrue(mock_provider1.aliases_processed.has_key(3))
        ## FIXME re-enable these tests after queue refactor in sprint 6
        ## self.assertFalse(mock_provider2.aliases_processed.has_key(3))
        ## self.assertEqual(pmt.queue.items[3].aliases.get_aliases_list(),[])

        # Check that item 4 was processed correctly, after retries
        ## FIXME re-enable this test after queue refactor in sprint 6                
        ## self.assertTrue(mock_provider1.aliases_processed.has_key(4))
        ## self.assertTrue(mock_provider2.aliases_processed.has_key(4))
        ## ns_list = [k for (k,v) in pmt.queue.items[4].aliases.get_aliases_list()]
        ## self.assertEqual(set(ns_list),set(['mock','doi']))


