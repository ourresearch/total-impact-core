import requests, os, unittest, time, threading, json
from totalimpact.providers.provider import Provider, ProviderFactory, ProviderHttpError, ProviderTimeout, ProviderState, ProviderError
from totalimpact.config import Configuration

CWD, _ = os.path.split(__file__)

def successful_get(url, headers=None, timeout=None):
    return url
def timeout_get(url, headers=None, timeout=None):
    raise requests.exceptions.Timeout()
def error_get(url, headers=None, timeout=None):
    raise requests.exceptions.RequestException()

class InterruptableSleepThread(threading.Thread):
    def run(self):
        provider = Provider(None, None)
        provider._interruptable_sleep(0.5)
    
    def _interruptable_sleep(self, snooze, duration):
        time.sleep(0.5)

class InterruptableSleepThread2(threading.Thread):
    def __init__(self, method, *args):
        super(InterruptableSleepThread2, self).__init__()
        self.method = method
        self.args = args
        
    def run(self):
        self.method(*self.args)
    
    def _interruptable_sleep(self, snooze, duration):
        time.sleep(snooze)

ERROR_CONF = json.loads('''
{
    "timeout" : { "retries" : 3, "retry_delay" : 1, "retry_type" : "linear", "delay_cap" : -1 },
    "http_error" : { "retries" : 0, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "client_server_error" : { },
    "rate_limit_reached" : { "retries" : -1, "retry_delay" : 1, "retry_type" : "incremental_back_off", "delay_cap" : 256 },
    "content_malformed" : { "retries" : 0, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "validation_failed" : { },
    
    "no_retries" : { "retries": 0 },
    "none_retries" : {},
    "one_retry" : { "retries" : 1 },
    "delay_2" : { "retries" : 2, "retry_delay" : 2 }
}
''')

class Test_Provider(unittest.TestCase):

    def setUp(self):
        self.config = Configuration()
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
        self.assertRaises(NotImplementedError, provider.biblio, None)
        
    def test_03_error(self):
        # FIXME: will need to test this when the error handling is written
        pass
        
    def test_04_sleep(self):
        provider = Provider(None, self.config)
        assert provider.sleep_time() == 0
    
    def test_incremental_back_off(self):
        provider = Provider(None, self.config)
        initial_delay = provider._incremental_back_off(1, 10, 1)
        assert initial_delay == 1
        
        subsequent_delay = provider._incremental_back_off(1, 10, 2)
        assert subsequent_delay == 2
        
        again_delay = provider._incremental_back_off(1, 10, 3)
        assert again_delay == 4
        
        big_delay = provider._incremental_back_off(1, 10, 8)
        assert big_delay == 10 # the delay cap
        
        sequence = [provider._incremental_back_off(2, 1000000, x) for x in range(1, 10)]
        compare = [2 * 2**(x-1) for x in range(1, 10)]
        assert sequence == compare, (sequence, compare)
    
    def test_linear_delay(self):
        provider = Provider(None, self.config)
        initial_delay = provider._linear_delay(1, 10, 10)
        assert initial_delay == 1
        
        another_delay = provider._linear_delay(10, 15, 10)
        assert another_delay == 10
        
        capped_delay = provider._linear_delay(10, 5, 10)
        assert capped_delay == 5
        
    def test_retry_wait(self):
        provider = Provider(None, self.config)
        linear_delay = provider._retry_wait("linear", 1, 10, 3)
        assert linear_delay == 1
        
        incremental_delay = provider._retry_wait("incremental_back_off", 1, 10, 3)
        assert incremental_delay == 4
        
        # anything unrecognised is treated as a linear delay
        other_delay = provider._retry_wait("whatever", 1, 10, 3)
        assert other_delay == 1
    
    def test_interruptable_sleep(self):
        provider = Provider(None, self.config)
        
        # this (nosetests) thread does not have the _interruptable_sleep method, so we 
        # should get an error
        self.assertRaises(Exception, provider._interruptable_sleep, 10)
        
        # now try kicking off an InterruptableSleepThread
        ist = InterruptableSleepThread()
        start = time.time()
        ist.start()
        ist.join()
        took = time.time() - start
        
        assert took > 0.5, took
        assert took < 1.0, took
    
    def test_snooze_or_raise_errors(self):
        provider = Provider(None, self.config)
        
        self.assertRaises(ProviderError, provider._snooze_or_raise, "whatever", ERROR_CONF, ProviderError(), 0)
        self.assertRaises(ProviderError, provider._snooze_or_raise, "no_retries", ERROR_CONF, ProviderError(), 0)
        self.assertRaises(ProviderError, provider._snooze_or_raise, "none_retries", ERROR_CONF, ProviderError(), 0)
        self.assertRaises(ProviderError, provider._snooze_or_raise, "one_retry", ERROR_CONF, ProviderError(), 2)
    
    def test_snooze_or_raise_defaults(self):
        provider = Provider(None, self.config)

        # delay of 0
        ist = InterruptableSleepThread2(provider._snooze_or_raise, "one_retry", ERROR_CONF, ProviderError(), 0)
        start = time.time()
        ist.start()
        ist.join()
        took = time.time() - start
        assert took > 0 and took < 0.1, took # has to be basically instantaneous
        
        # retry_type of linear
        ist = InterruptableSleepThread2(provider._snooze_or_raise, "delay_2", ERROR_CONF, ProviderError(), 1)
        start = time.time()
        ist.start()
        ist.join()
        took = time.time() - start
        assert took > 1.9 and took < 2.5, took
    
    def test_snooze_or_raise_success(self):
        provider = Provider(None, self.config)
        # do one which provides all its own configuration arguments
        ist = InterruptableSleepThread2(provider._snooze_or_raise, "timeout", ERROR_CONF, ProviderError(), 0)
        start = time.time()
        ist.start()
        ist.join()
        took = time.time() - start
        assert took > 0.9 and took < 1.1, took # has to be basically instantaneous
    
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
        assert provider.id == "wikipedia"
        
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