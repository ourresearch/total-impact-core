import time, threading, random

class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
    
    def _interruptable_sleep(self, duration, increment=0.5):
        if duration <= 0:
            return
        slept = 0
        while not self.stopped() and slept < duration:
            snooze = increment if duration - slept > increment else duration - slept
            time.sleep(snooze)
            slept += snooze

class ProviderMetricsThread(StoppableThread):
    
    def __init__(self, rate_period=3600, rate_limit=350, 
                    time_fixture=None, last_request_time=None, request_count=0):
        super(ProviderMetricsThread, self).__init__()
        self.time_fixture = time_fixture
        self.last_request_time = last_request_time
        self.rate_period = rate_period
        
        # scale the rate limit to avoid double counting
        self.rate_limit = rate_limit + 1
        self.request_count = request_count
        
    # NOTE, can, theoretically return negative numbers ... this should be ok
    def _get_seconds(self, remaining_time, remaining_requests, request_time):
        if remaining_requests <= 0:
            # wait until the reset time
            return self._get_reset_time(request_time) - request_time
        return remaining_time / float(remaining_requests)
    
    # get the timestamp which represents when the rate counter will reset
    def _get_reset_time(self, request_time):
        # The reset time is at the start of the next rating period
        # after the time fixture.  If there is no time fixture,
        # then that time starts now
        if self.time_fixture is None:
            return request_time
        return self.time_fixture + self.rate_period
    
    def _rate_limit_expired(self, request_time):
        return self.time_fixture + self.rate_period < request_time
    
    def _get_remaining_time(self, request_time):
        remaining_time = (self.time_fixture + self.rate_period) - request_time
        #since_last = request_time - self.last_request_time
        #remaining_time = self.rate_period - since_last
        return remaining_time
    
    # FIXME: this can double count requests, which matters on very high
    # rate limits.  E.g. 3/second comes out at one at 0.0, 0.5 and 1.0,
    # but by this time the rate limit has expired, and we should be able 
    # to request 1.0, 1.5 and 2.0.  So the requests at 1.0 are double
    # counted
    def sleep_time(self):
        # set ourselves a standard time entity to use in all our
        # calculations
        request_time = time.time()
        
        # always pre-increment the request count, since we assume that we
        # are being called after the request, not before
        self.request_count += 1
        
        if self.last_request_time is None or self.time_fixture is None:
            # if there have been no previous requests, set the current last_request
            # time and the time_fixture to now
            self.time_fixture = request_time
            self.last_request_time = request_time
        
        # has the rate limiting period expired?  If so, set the new fixture
        # to now, and reset the request counter (which we start from 1,
        # for reasons noted above), and allow the caller to just go
        # right ahead by returning a 0.0
        if self._rate_limit_expired(request_time):
            self.time_fixture = request_time
            self.last_request_time = request_time
            self.request_count = 1
            return 0.0
        
        # calculate how many requests we have left in the current period
        # this number could be negative if the caller is ignoring our sleep
        # time suggestions
        remaining_requests = self.rate_limit - self.request_count
        
        # get the time remaining in this rate_period.  This does not take
        # into account whether the caller has obeyed our sleep time suggestions
        remaining_time = self._get_remaining_time(request_time)
        
        # NOTE: this will always return a number less than or equal to the time
        # until the next rate limit period is up.  It does not attempt to deal
        # with rate limit excessions
        #
        # calculate the amount of time to sleep for
        sleep_for = self._get_seconds(remaining_time, remaining_requests, request_time)
        
        # remember the time of /this/ request, so that it can be re-used 
        # on next call
        self.last_request_time = request_time
        
        # tell the caller how long to sleep for
        return sleep_for
    
    def process(self):
        time.sleep(random.random())
    
    def run(self):
        i = 0
        while not self.stopped() and i < 500:
            start = time.time()
            i += 1
            
            # Whatever processing job is required
            item = self.process()
            
            processed = time.time()
            
            # the provider will return a sleep time which may be negative
            sleep_time = self.sleep_time()
            
            print start, processed, sleep_time
            
            if sleep_time != 0:
                # sleep
                self._interruptable_sleep(sleep_time)
                