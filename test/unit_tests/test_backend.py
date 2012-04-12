import os, unittest, time
from nose.tools import nottest, assert_equals

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
from totalimpact import dao, api
from totalimpact.tilogging import logging

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

class QueueMock(object):
    def __init__(self):
        self.none_count = 0
    def first(self):
        if self.none_count >= 3:
            return ItemMock()
        else:
            self.none_count += 1
            return None
    def save_and_unqueue(self, item):
        pass

class ItemMock(object):
    def aliases(self, item):
        return item

class ProviderMock(Provider):
    def __init__(self, id=None):
        Provider.__init__(self, None)
        self.id = id
    def aliases(self, item):
        return item
    def metrics(self, item):
        return item
    def provides_metrics(self):
        return True
        
class ProviderNotImplemented(Provider):
    def __init__(self):
        Provider.__init__(self, None)
        self.id = None
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
        TEST_DB_URL = "http://localhost:5984/"
        TEST_PROVIDER_CONFIG = [{
            "class" : "totalimpact.providers.wikipedia.Wikipedia",
            "config" : "totalimpact/providers/wikipedia.conf.json"
        }]

        self.d = dao.Dao(TEST_DB_NAME, TEST_DB_URL)        
        self.d.create_new_db_and_connect(TEST_DB_NAME)

        self.queue_first = Queue.first
        Queue.first = first_mock
        
        self.queue_save_and_unqueue = Queue.save_and_unqueue
        Queue.save_and_unqueue = save_and_unqueue_mock
        
        self.metrics_queue_save_and_unqueue = MetricsQueue.save_and_unqueue
        MetricsQueue.save_and_unqueue = save_and_unqueue_mock
        
        self.get_providers = ProviderFactory.get_providers
        ProviderFactory.get_providers = classmethod(get_providers_mock)

        self.providers = self.get_providers(TEST_PROVIDER_CONFIG)
        
    def tearDown(self):
        Queue.first = self.queue_first
        Queue.save_and_unqueue = self.queue_save_and_unqueue
        MetricsQueue.save_and_unqueue = self.metrics_queue_save_and_unqueue
        
        # FIXME: check that this doesn't need to be wrapped in a classmethod() call
        ProviderFactory.get_providers = self.get_providers

    def test_01_init_backend(self):
        watcher = TotalImpactBackend(self.d, self.providers)
        
        assert len(watcher.threads) == 0
        assert len(watcher.providers) == len(self.providers), len(watcher.providers)
        
    def test_02_init_metrics(self):
        provider = Provider(None)
        provider.id = "test"
        pmt = ProviderMetricsThread(provider, self.d)
        
        assert hasattr(pmt, "stop")
        assert hasattr(pmt, "stopped")
        assert hasattr(pmt, "first")
        assert pmt.queue is not None
        assert pmt.provider.id == "test"
        assert pmt.queue.provider == "test"
        
    def test_03_init_aliases(self):
        providers = ProviderFactory.get_providers(self.config)
        pat = ProvidersAliasThread(providers, self.d)
        
        assert hasattr(pat, "stop")
        assert hasattr(pat, "stopped")
        assert hasattr(pat, "first")
        assert pat.queue is not None
        
    def test_04_alias_sleep(self):
        providers = ProviderFactory.get_providers(self.config)
        pat = ProvidersAliasThread(providers, self.d)
        assert pat.sleep_time() == 0
        
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
        assert took < 3.2
        
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

    def test_14_backend(self):
        watcher = TotalImpactBackend(self.d, self.providers)
        
        watcher._spawn_threads()
        assert len(watcher.threads) == len(self.providers)+1, len(watcher.threads)
        
        watcher._cleanup()
        assert len(watcher.threads) == 0, len(watcher.threads)
