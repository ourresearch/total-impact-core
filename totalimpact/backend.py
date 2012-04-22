import threading, time, sys
import traceback
from totalimpact.config import Configuration
from totalimpact import dao, api
from totalimpact.queue import AliasQueue, MetricsQueue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.models import Error

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)

from totalimpact.providers.provider import ProviderConfigurationError, ProviderTimeout, ProviderHttpError
from totalimpact.providers.provider import ProviderClientError, ProviderServerError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderValidationFailedError, ProviderRateLimitError


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



class ProviderThread(QueueConsumer):
    """ This is the basis for the threads processing items for a provider

        Subclasses should implement process_item to define how they want
        to use providers to obtain information about a given item. The
        method process_item_for_provider defined by this class should then
        be used to handle those updates. This method will deal with retries
        and backoff as per the provider configuration.  

        This base class is mostly to avoid code duplication between the 
        Metric and Alias providers.
    """

    def __init__(self, dao, queue):
        self.dao = dao
        QueueConsumer.__init__(self, queue)
        self.thread_id = "BaseProviderThread"
        self.run_once = False

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

    def run(self, run_only_once=False):

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

            # Flag for testing. We should finish the run loop as soon
            # as we've processed a single item.
            if run_only_once:
                return

    def process_item_for_provider(self, item, provider, method):
        """ Run the given method for the given provider on the given item
        
            method should either be 'aliases', 'biblio', or 'metrics'

            This will deal with retries and sleep / backoff as per the 
            configuration for the given provider. We will return true if
            the given method passes, or if it's not implemented.
        """
        if method not in ('aliases', 'biblio', 'metrics'):
            raise NotImplementedError("Unknown method %s for provider class" % method)

        log.info("Item %s: processing %s for provider %s" % (item, method, provider))
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
            provider_function = getattr(provider, method)
            try:
                response = provider_function(item)
                if "metrics" in method:
                    item.metrics = response
                else:
                    item = response
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

            except NotImplementedError, e:
                # This means we should skip aliases for this provider
                # Don't record any failures here, just set success as true so we exit
                # Success = true will mean that we continue processing this item
                log.debug("Processing item %s with provider %s: Unknown exception %s, aborting" % (item, provider, e))
                success = True

            except Exception, e:
                # All other fatal errors. These are probably some form of
                # logic error. We consider these to be fatal.
                tb = sys.exc_info()[2]
                self.log_error(item, 'unknown_error', str(e), tb)
                log.error("Error processing item %s with provider %s: Unknown exception %s, aborting" % (item, provider, e))
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

                    max_retries = provider.get_max_retries(error_type)
                    if error_counts[error_type] > max_retries and max_retries != -1:
                        log.info("Error processing item %s: %s, error limit reached (%i/%i), aborting" % (
                            item, error_type, error_counts[error_type], max_retries))
                        error_limit_reached = True
                    else:
                        duration = provider.get_sleep_time(error_type, error_counts[error_type])
                        log.info("Error processing item %s: %s, pausing thread for %s" % (item, error_type, duration))
                        self._interruptable_sleep(duration)
                elif success:
                    log.info("Item %s: processing successful" % (item))

        return success


class ProvidersAliasThread(ProviderThread):
    
    def __init__(self, providers, dao):
        self.providers = providers
        queue = AliasQueue(dao)
        ProviderThread.__init__(self, dao, queue)
        self.providers = providers
        self.thread_id = "ProvidersAliasThread"
        
    def process_item(self, item):
        """ Process the given item, obtaining it's metrics.

            This method will retry for the appropriate number of times, sleeping
            if required according to the config settings.
        """
        if not self.stopped():
            for provider in self.providers: 
                if not self.process_item_for_provider(item, provider, 'aliases'):
                    # This provider has failed and exceeded the 
                    # total number of retries. Don't process any 
                    # more providers, we abort this item entirely
                    break
                if not self.process_item_for_provider(item, provider, 'biblio'):
                    # This provider has failed and exceeded the 
                    # total number of retries. Don't process any 
                    # more providers, we abort this item entirely
                    break



class ProviderMetricsThread(ProviderThread):
    """ The provider metrics thread will handle obtaining metrics for all
        requests for a single provider. It will deal with retries and 
        timeouts as required.
    """
    def __init__(self, provider, dao):
        self.provider = provider
        queue = MetricsQueue(dao, provider.id)
        ProviderThread.__init__(self, dao, queue)
        self.thread_id = "ProviderMetricsThread:" + str(self.provider.id)

    def process_item(self, item):
        success = self.process_item_for_provider(item, 
            self.provider, 
            'metrics')
        return success
