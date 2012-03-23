import requests, os, unittest, time
from totalimpact.providers.provider import Provider, ProviderFactory, ProviderHttpError, ProviderTimeout, ProviderState
from totalimpact.config import Configuration

CWD, _ = os.path.split(__file__)

APP_CONFIG = os.path.join(CWD, "test.conf.json")

def successful_get(url, headers=None, timeout=None):
    return url
def timeout_get(url, headers=None, timeout=None):
    raise requests.exceptions.Timeout()
def error_get(url, headers=None, timeout=None):
    raise requests.exceptions.RequestException()

class Test_Provider(unittest.TestCase):

    def setUp(self):
        print APP_CONFIG
        self.config = Configuration(APP_CONFIG, False)
        self.old_http_get = requests.get
    
    def tearDown(self):
        requests.get = self.old_http_get
    
    def test_01_init(self):
        # since the provider is really abstract, this doen't
        # make much sense, but we do it anyway
        provider = Provider(None, self.config)

    def test_02_interface(self):
        # check that the interface is defined, and has appropriate
        # defaults/NotImplementedErrors
        provider = Provider(None, self.config)
        
        assert not provider.provides_metrics()
        self.assertRaises(NotImplementedError, provider.member_items, None, None)
        self.assertRaises(NotImplementedError, provider.aliases, None)
        self.assertRaises(NotImplementedError, provider.metrics, None)
        
    def test_03_error(self):
        # FIXME: will need to test this when the error handling is written
        pass
        
    def test_04_sleep(self):
        provider = Provider(None, self.config)
        assert provider.sleep_time() == 0
        
    def test_05_request_error(self):
        requests.get = error_get
        
        provider = Provider(None, self.config)
        self.assertRaises(ProviderHttpError, provider.http_get, "", None, None)
        
        requests.get = self.old_http_get
        
    def test_06_request_error(self):
        requests.get = timeout_get
        
        provider = Provider(None, self.config)
        self.assertRaises(ProviderTimeout, provider.http_get, "", None, None)
        
        requests.get = self.old_http_get
        
    def test_07_request_error(self):
        requests.get = successful_get
        
        provider = Provider(None, self.config)
        r = provider.http_get("test")
        
        assert r == "test"
        
        requests.get = self.old_http_get
        
    # FIXME: we will also need tests to cover the cacheing when that
    # has been implemented
    
    def test_08_get_provider(self):
        pconf = None
        for p in self.config.providers:
            if p["class"].endswith("wikipedia.Wikipedia"):
                pconf = p
                break
        provider = ProviderFactory.get_provider(pconf, self.config)
        assert provider.id == "Wikipedia"
        
    def test_09_get_providers(self):
        providers = ProviderFactory.get_providers(self.config)
        assert len(providers) == len(self.config.providers)

    def test_10_state_init(self):
        s = ProviderState()
        
        assert s.throttled
        assert s.time_fixture is None
        assert s.last_request_time is None
        assert s.rate_period == 3600
        assert s.rate_limit == 351
        assert s.request_count == 0
        
        now = time.time()
        s = ProviderState(rate_period=100, rate_limit=100, 
                    time_fixture=now, last_request_time=now, request_count=7,
                    throttled=False)
        
        assert not s.throttled
        assert s.time_fixture == now
        assert s.last_request_time == now
        assert s.rate_period == 100
        assert s.rate_limit == 101
        assert s.request_count == 7
        
    def test_11_state_hit(self):
        s = ProviderState()
        s.register_unthrottled_hit()
        assert s.request_count == 1
    
    def test_12_state_get_reset_time(self):
        now = time.time()
        
        s = ProviderState()
        reset = s._get_reset_time(now)
        assert reset == now
        
        s = ProviderState(rate_period=100, time_fixture=now)
        reset = s._get_reset_time(now + 10)
        assert reset == now + 100
        
    def test_13_state_get_seconds(self):
        now = time.time()
        
        s = ProviderState(rate_period=100, time_fixture=now)
        seconds = s._get_seconds(100, 0, now + 10)
        assert seconds == 90, seconds
        
        s = ProviderState()
        seconds = s._get_seconds(100, 50, now)
        assert seconds == 2, seconds
        
    def test_14_state_rate_limit_expired(self):
        now = time.time()
        
        s = ProviderState(rate_period=100, time_fixture=now)
        assert not s._rate_limit_expired(now + 10)
        assert s._rate_limit_expired(now + 101)
        
    def test_15_state_get_remaining_time(self):
        now = time.time()
        s = ProviderState(rate_period=100, time_fixture=now)
        remaining = s._get_remaining_time(now + 10)
        assert remaining == 90
        
    def test_15_state_sleep_time(self):
        now = time.time()
        
        s = ProviderState(throttled=False)
        sleep = s.sleep_time()
        assert sleep == 0.0, sleep
        
        s = ProviderState(rate_period=100, time_fixture=now-100, last_request_time=now-100)
        sleep = s.sleep_time()
        assert sleep == 0.0, sleep
        
        s = ProviderState(rate_period=100, rate_limit=100)
        sleep = s.sleep_time()
        assert sleep == 1.0, sleep