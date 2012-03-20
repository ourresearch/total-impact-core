import os, unittest, time
from totalimpact.watchers import Watchers, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.config import Configuration
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import AliasQueue, MetricsQueue

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "test.conf.json")

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
class ItemMock(object):
    pass

class ProviderMock(Provider):
    def __init__(self):
        Provider.__init__(self, None, None)
    def aliases(self, item):
        return item
        
class ProviderNotImplemented(Provider):
    def __init__(self):
        Provider.__init__(self, None, None)
    def aliases(self, item):
        raise NotImplementedError()

def alias_first_mock(self):
    return ItemMock()

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
        
    def test_05_run_stop(self):
        st = StoppableThread()
        assert not st.stopped()
        
        st.stop()
        assert st.stopped()
        
    def test_06_sleep_interrupt(self):
        st = StoppableThread()
        
        # basic interruptable sleep
        start = time.time()
        st._interruptable_sleep(2)
        took = time.time() - start
        assert took < 2.5 # take into account interval on interruptable sleep
        
        # advanced interruptable sleep
        start = time.time()
        st._interruptable_sleep(3, 0.1)
        took = time.time() - start
        assert took < 3.1
        
        # now try interrupting the sleep (need to use a special wrapper
        # class defined above to get this done)
        start = time.time()
        InterruptTester().run(2)
        took = time.time() - start
        assert took < 2.5

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
        AliasQueue.first = alias_first_mock
        providers = [ProviderMock()]
        pat = ProvidersAliasThread(providers, self.config)
        
        pat.start()
        pat.stop()
        pat.join()
        
        # there are no assertions to make here, only that the
        # test completes without error
        assert True
        
    def test_09_alias_running(self):
        AliasQueue.first = alias_first_mock
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
        
    def test_10_alias_provider_not_implemented(self):
        AliasQueue.first = alias_first_mock
        providers = [ProviderNotImplemented()] 
        pat = ProvidersAliasThread(providers, self.config)
        
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