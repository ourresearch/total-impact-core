import threading, time, sys
import traceback
from totalimpact.config import Configuration
from totalimpact import dao, api
from totalimpact.queue import AliasQueue, MetricsQueue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.models import Error

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)


class TotalImpactBackend(object):
    
    def __init__(self, dao, providers):
        self.threads = [] 
        self.dao = dao
        self.providers = providers
    
    def run(self):
        self._spawn_threads()
        try:
            self._monitor()
        except (KeyboardInterrupt, SystemExit):
            log.info("Interrupted ... exiting ...")
            self._cleanup()
    
    def _spawn_threads(self):
        
        for provider in self.providers:
            if not provider.provides_metrics():
                continue
            log.info("Spawning thread for provider " + str(provider.id))
            # create and start the metrics threads
            t = ProviderMetricsThread(provider, self.dao)
            t.start()
            self.threads.append(t)
        
        log.info("Spawning thread for aliases")
        alias_thread = ProvidersAliasThread(self.providers, self.dao)
        alias_thread.start()
        self.threads.append(alias_thread)
        
    def _monitor(self):        
        while True:
            # just spin our wheels waiting for interrupts
            time.sleep(1)
    
    def _cleanup(self):
        for t in self.threads:
            log.info("Stopping " + t.thread_id)
            t.stop()
            t.join()
            log.info("... stopped")
        self.threads = []
    

           
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



class QueueConsumer(StoppableThread):

    def __init__(self, queue):
        StoppableThread.__init__(self)
        self.queue = queue
    
    def first(self):
        # get the first item on the queue (waiting until there is
        # such a thing if necessary)
        item = None
        while item is None and not self.stopped():
            item = self.queue.first()
            if item is None:
                # if the queue is empty, wait 0.5 seconds before checking
                # again
                time.sleep(0.5)
        return item

# NOTE: provider aliases does not throttle or take into account
# provider sleep times.  This is fine for the time being, as 
# aliasing is an urgent request.  The provider should count the
# requests as they happen, so that the metrics thread can keep itself
# in check to throttle the api requests.
class ProvidersAliasThread(QueueConsumer):
    run_once = False
    def __init__(self, providers, dao):
        QueueConsumer.__init__(self, AliasQueue(dao))
        self.providers = providers
        self.thread_id = "ProvidersAliasThread"
        
    def run(self):
        while not self.stopped():

            # get the first item on the queue - this waits until
            # there is something to return
            item = self.first()
            
            # Check we have an item, if we have been signalled to stop, then
            # item may be None
            if item:
                # if we get to here, an item has been popped off the queue and we
                # now want to calculate it's metrics. 
                # Repeatedly process this item until we hit the error limit
                # or we successfully process it         
                self.process_item(item) 

    def process_item(self, item):
        if not self.stopped():
            for p in self.providers: 
                try:
                    log.info("in ProvidersAliasThread.run")

                    item = p.aliases(item)
                    self.queue.save_and_unqueue(item)
                    if self.run_once:
                        self.stop()
                except NotImplementedError:
                    continue
            
            self._interruptable_sleep(self.sleep_time())
            
    def sleep_time(self):
        # just keep punting through the aliases as fast as possible for the time being
        return 0



from totalimpact.providers.provider import ProviderConfigurationError, ProviderTimeout, ProviderHttpError
from totalimpact.providers.provider import ProviderClientError, ProviderServerError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderValidationFailedError, ProviderRateLimitError



class ProviderMetricsThread(QueueConsumer):
    """ The provider metrics thread will handle obtaining metrics for all
        requests for a single provider. It will deal with retries and 
        timeouts as required.
    """

    def __init__(self, provider, dao):
        QueueConsumer.__init__(self, MetricsQueue(dao, provider.id))
        self.provider = provider
        self.dao = dao
        self.thread_id = "ProviderMetricsThread:" + str(self.provider.id)

    def log_error(self, item, error_type, error_msg, tb):
        # This method is called to record any errors which we obtain when
        # trying process an item.
        logger = logging.getLogger('backend')
        logger.error("exception for item(%s): %s (%s)" % (item.id, error_msg, error_type))
        
        e = Error(self.dao)
        e.message = error_msg
        e.error_type = error_type
        e.id = item.id
        e.provider = self.thread_id
        e.stack_trace = "".join(traceback.format_tb(tb))
        
        logger.debug(str(e.stack_trace))
        
        #e.save()

    def get_sleep_time(self, error_type, retry_count): 
        """ Find out how long we should sleep for the given error type and count
 
            error_type - timeout, http_error, ... should match config
            retry_count - this will be our n-th retry (first retry is 1)
        """ 
        error_conf = self.provider.config.errors
        if error_conf is None: 
            raise Exception("Provider has no config for error handling")
         
        conf = error_conf.get(error_type) 
        if conf is None: 
            raise Exception("Provider has no config for error handling for error type %s" % error_type)
         
        retries = conf.get("retries") 
        if retries is None or retries == 0: 
            raise exception 

        delay = conf.get("retry_delay", 0) 
        delay_cap = conf.get("delay_cap", -1) 
        retry_type = conf.get("retry_type", "linear") 
         
        # Check we haven't reached max retries
        if retry_count > retries and retries != -1: 
            raise ValueError("Exceeded max retries for %s" % error_type)

        # Linear or exponential delay
        if retry_type == 'linear':
            delay_time = delay
        else:
            delay_time = delay * 2**(retry_count-1) 
    
        # Apply delay cap, which limits how long we can sleep
        if delay_cap != -1:
            delay_time = min(delay_cap, delay_time)
        
        return delay_time

    def get_max_retries(self, error_type):
        error_conf = self.provider.config.errors
        if error_conf is None: 
            raise Exception("Provider has no config for error handling")
         
        conf = error_conf.get(error_type) 
        if conf is None: 
            raise Exception("Provider has no config for error handling for error type %s" % error_type)
         
        retries = conf.get("retries") 
        if retries is None:
            return 0
        return retries
         
    def run(self):

        while not self.stopped():

            # get the first item on the queue - this waits until
            # there is something to return
            item = self.first()
            
            # Check we have an item, if we have been signalled to stop, then
            # item may be None
            if item:
                # if we get to here, an item has been popped off the queue and we
                # now want to calculate it's metrics. 
                # Repeatedly process this item until we hit the error limit
                # or we successfully process it         
                self.process_item(item) 

                # Either this item was successfully process, or we failed for 
                # an excessive number of retries. Either way, update the item
                # as we don't process it again a second time.
                self.queue.save_and_unqueue(item)

                # the provider will return a sleep time which may be negative
                # this is our base sleep time between requests
                #sleep_time = self.provider.sleep_time()
                #self._interruptable_sleep(sleep_time)


    def process_item(self, item):
        """ Process the given item, obtaining it's metrics.

            This method will retry for the appropriate number of times, sleeping
            if required according to the config settings.
        """
        log.info("Item %s: processing metrics" % (item))
        error_counts = {
            'http_timeout':0,
            'content_malformed':0,
            'validation_failed':0,
            'client_server_error':0,
            'rate_limit_reached':0,
            'http_error':0
        }
        success = False
        error_limit_reached = False

        while not error_limit_reached and not success and not self.stopped():

            error_type = None
            try:
                item = self.provider.metrics(item)
                success = True

            except ProviderTimeout, e:
                error_type = 'http_timeout'
                error_msg = str(e)
            except ProviderRateLimitError, e:
                error_type = 'rate_limit_reached'
                error_msg = str(e)
            except ProviderHttpError, e:
                error_type = 'http_error'
                error_msg = str(e)
            except (ProviderClientError,ProviderServerError,ProviderConfigurationError), e:
                error_type = 'client_server_error'
                error_msg = str(e)
            except ProviderContentMalformedError, e:
                error_type = 'content_malformed'
                error_msg = str(e)
            except ProviderValidationFailedError, e:
                error_type = 'validation_failed'
                error_msg = str(e)

            except Exception, e:
                # All other fatal errors. These are probably some form of
                # logic error. We consider these to be fatal.
                tb = sys.exc_info()[2]
                self.log_error(item, 'unknown_error', str(e), tb)
                log.error("Error processing item %s: Unknown exception %s, aborting" % (item, e))
                error_limit_reached = True

            finally:
                # If we had any errors, update the error counts and sleep if 
                # we need to do so, before retrying. If we exceed the error limit
                # for the given error type, set error_limit_reached to be true

                if error_type:
                    # Log the error and it's traceback
                    tb = sys.exc_info()[2]
                    self.log_error(item, error_type, error_msg, tb)

                    error_counts[error_type] += 1

                    if error_counts[error_type] > self.get_max_retries(error_type) and self.get_max_retries(error_type) != -1:
                        log.info("Error processing item %s: %s, error limit reached (%i/%i), aborting" % (
                            item, error_type, error_counts[error_type], self.get_max_retries(error_type)))
                        error_limit_reached = True
                    else:
                        duration = self.get_sleep_time(error_type, error_counts[error_type])
                        log.info("Error processing item %s: %s, pausing thread for %s" % (item, error_type, duration))
                        self._interruptable_sleep(duration)
                elif success:
                    log.info("Item %s: processing successful" % (item))

        return success
            
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Please supply the path to the configuration file"
    else:
        TotalImpactBackend(Configuration(sys.argv[1])).run()
