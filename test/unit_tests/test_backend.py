import os, unittest, time, logging
from nose.tools import nottest, assert_equals
from test.utils import slow

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread
from totalimpact.providers.provider import Provider, ProviderFactory, ProviderTimeout
from totalimpact import dao, tiredis, backend


TEST_DB_NAME = "test_dao"

#@TODO this needs lots and lots of work, including using the same local db test
# approach that test_views.py uses.


from test.mocks import ProviderMock, QueueMock

def slow(f):
    f.slow = True
    return f

logging.disable(logging.CRITICAL)
CWD, _ = os.path.split(__file__)

TIME_SCALE = 0.0005 #multiplier to run the tests as fast as possible
BACKEND_POLL_INTERVAL = 0.5 #seconds

class ProviderNotImplemented(Provider):
    def __init__(self):
        Provider.__init__(self, None)
        self.provider_name = 'not_implemented'
    def aliases(self, item, provider_url_template=None, cache_enabled=True):
        raise NotImplementedError()
    def metrics(self, item, provider_url_template=None, cache_enabled=True):
        raise NotImplementedError()


def save_and_unqueue_mock(self, item):
    pass
    
def get_providers_mock(cls, config):
    return [ProviderMock("1"), ProviderMock("2"), ProviderMock("3")]



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
    return {"_id": "testitemid"}

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
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))

        # do the same thing for the redis db
        self.r = tiredis.from_url("redis://localhost:6379")
        self.r.flushdb()


        self.providers = [ProviderMock("1"), ProviderMock("2"), ProviderMock("3")]
        self.item_with_aliases = {
            "_id": "1",
            "type": "item",
            "num_providers_still_updating":1,
            "aliases":{"pmid":["111"]},
            "biblio": {},
            "metrics": {}
        }
        
        
    def teardown(self):
        pass
        self.d.delete_db(os.environ["CLOUDANT_DB"])



class TestAliasesWorker(TestBackend):

    @nottest
    def test_update(self):
        aw = backend.ProvidersAliasThread(providers=[self.providers[0]])
        new_item = aw.update(self.item_with_aliases, override=True)
        print new_item
        assert_equals(
            new_item["aliases"]["doi"][0],
            "10.1"
        )

    @nottest
    def test_update_with_another_doi(self):
        # put a doi in the item
        aw = backend.ProvidersAliasThread(providers=[self.providers[0]])
        item_with_doi = aw.update(self.item_with_aliases, override=True)

        # another provider also gets dois...
        self.providers[1].aliases_returns = [("doi", "10.2")]
        aw = backend.ProvidersAliasThread(providers=[self.providers[1]])
        item_with_two_dois = aw.update(item_with_doi, override=True)

        print item_with_two_dois
        assert_equals(
            item_with_two_dois["aliases"]["doi"],
            ["10.1", "10.2"]
        )

    @nottest
    def test_update_with_provider_timeout(self):
        self.providers[0].exception_to_raise = ProviderTimeout
        aw = backend.ProvidersAliasThread(providers=[self.providers[0]])
        new_item = aw.update(self.item_with_aliases)
        print new_item

        assert_equals(len(new_item["aliases"]), 1) # new alias not added

  

class TestOldBackend():
    
    def setUp(self):
        self.config = None #placeholder
        TEST_PROVIDER_CONFIG = [
            ("wikipedia", {})
        ]
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))

        # do the same thing for the redis db
        self.r = tiredis.from_url("redis://localhost:6379")
        self.r.flushdb()

        self.get_providers = ProviderFactory.get_providers
        ProviderFactory.get_providers = classmethod(get_providers_mock)

        self.providers = self.get_providers(TEST_PROVIDER_CONFIG)
        
        
    def teardown(self):
        # FIXME: check that this doesn't need to be wrapped in a classmethod() call
        ProviderFactory.get_providers = self.get_providers
        self.d.delete_db(os.environ["CLOUDANT_DB"])

    def test_01_init_backend(self):
        watcher = TotalImpactBackend(self.d, self.r, self.providers)
        
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
        pat = ProvidersAliasThread([], self.d, self.r, providers)
        pat.queue = QueueMock()
        
        pat.start()
        pat.stop()
        pat.join()
        
        # there are no assertions to make here, only that the
        # test completes without error
        assert True
       
    def test_12_metrics_stopped(self):
        # relies on Queue.first mock as per setUp
        pmt = ProviderMetricsThread([], self.d, self.r, ProviderMock())
        pmt.queue = QueueMock()
        
        pmt.start()
        pmt.stop()
        pmt.join()
        
        # there are no assertions to make here, only that the
        # test completes without error
        assert True
        
 

 
