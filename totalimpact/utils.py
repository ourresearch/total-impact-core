import time
import logging

logger = logging.getLogger('ti.utils')

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
                    logger.debug(u"Retry: "+e.__repr__())
                    time.sleep(self.delay)
                    exception = e

            #if no success after tries, could raise last exception here...

            logger.debug(u"Tried mightily, but giving up after {tries} '{exception_type}' exceptions.".format(
                tries=self.tries,
                exception_type=e.__repr__()
            ))

            return False # fail silently...
        return fn

