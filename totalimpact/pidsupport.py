import threading
import time
import logging

logger = logging.getLogger('ti.pidsupport')

class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()
        self.sleeping = False

    def run(self):
        # NOTE: subclasses MUST override this - this behaviour is
        # only for testing purposes

        # go into a restless but persistent sleep (in 60 second
        # batches)
        while not self.stopped():
            self._interruptable_sleep(60)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def _interruptable_sleep(self, duration, increment=0.5):
        self.sleeping = True
        if duration <= 0:
            return
        slept = 0
        while not self.stopped() and slept < duration:
            snooze = increment if duration - slept > increment else duration - slept
            time.sleep(snooze)
            slept += snooze
        self.sleeping = False



class Retry(object):
    default_exceptions = (Exception,)
    def __init__(self, tries, exceptions=None, delay=0):
        """
        Decorator for retrying a function if exception occurs

        tries -- num tries
        exceptions -- exceptions to catch
        delay -- wait between retries
        from http://peter-hoffmann.com/2010/retry-decorator-python.html
        """
        self.tries = tries
        if exceptions is None:
            exceptions = Retry.default_exceptions
        self.exceptions =  exceptions
        self.delay = delay

    def __call__(self, f):
        def fn(*args, **kwargs):
            exception = None
            for _ in range(self.tries):
                try:
                    return f(*args, **kwargs)
                except self.exceptions, e:
                    logger.debug("Retry, exception: "+e.__repr__())
                    time.sleep(self.delay)
                    exception = e

            #if no success after tries, could raise last exception here...

            logger.debug("Tried mightily, but giving up after {tries} '{exception_type}' exceptions.".format(
                tries=self.tries,
                exception_type=e.__repr__()
            ))

            return False # fail silently...
        return fn