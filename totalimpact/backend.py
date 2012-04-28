import threading, time, sys
import traceback
from totalimpact.config import Configuration
from totalimpact import dao, api
from totalimpact.queue import AliasQueue, MetricsQueue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.models import Error

from totalimpact.tilogging import logging

from totalimpact.providers.provider import ProviderConfigurationError, ProviderTimeout, ProviderHttpError
from totalimpact.providers.provider import ProviderClientError, ProviderServerError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderValidationFailedError, ProviderRateLimitError

logger = logging.getLogger('backend')

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


class ContextFilter(logging.Filter):
    """ Filter to add contextual information regarding items to logs

        This filter will check the thread local storage to see if we have
        recorded that we are processing an item. If so, we will add this 
        into the formatter so that the logs print it.
    """
    def __init__(self):
        # Check thread local storage
        self.local = threading.local()

    def threadInit(self):
        """ All threads should call this to set up the context object """
        self.local.backend = {
            'item': '',
            'method': '',
            'provider': '',
            'thread': ''
        }

    def filter(self, record):
    
        # Attempt to get values. Any problems, just assume empty
        item = method = provider = thread = ""
        try:
            item = self.local.backend['item']
            method = self.local.backend['method']
            provider = self.local.backend['provider']
            thread = self.local.backend['thread']
        except (AttributeError, KeyError), e:
            pass

        # Store context information for logger to print
        record.item = item
        record.method = method
        record.provider = provider
        record.thread = thread
        return True

ctxfilter = ContextFilter()

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
        logger.error("exception for item(%s): %s (%s)" % (item.id, error_msg, error_type))
        
        e = Error(self.dao)
        e.message = error_msg
        e.error_type = error_type
        e.id = item.id
        e.provider = self.thread_id
        e.stack_trace = "".join(traceback.format_tb(tb))
        
        logger.debug(str(e.stack_trace))
        
        #e.save()

    def startup(self):
        # Ensure logs for this thread are marked correctly
        ctxfilter.threadInit()

    def run(self, run_only_once=False):
        self.startup()

        while not self.stopped():
            # get the first item on the queue - this waits until
            # there is something to return
            logger.debug("%s - waiting for queue item" % self.thread_id)
            item = self.first()
            
            # Check we have an item, if we have been signalled to stop, then
            # item may be None
            if item:
                # if we get to here, an item has been popped off the queue and we
                # now want to calculate it's metrics. 
                # Repeatedly process this item until we hit the error limit
                # or we successfully process it         
                ctxfilter.local.backend['item'] = item.id
                logger.debug("Processing New Item ===================================")
                self.process_item(item) 

                # Either this item was successfully process, or we failed for 
                # an excessive number of retries. Either way, update the item
                # as we don't process it again a second time.
                logger.debug("Processing Complete: Unqueue Item =====================")
                self.queue.save_and_unqueue(item)
                ctxfilter.local.backend['item'] = ''

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
        
        logger.info("processing %s for provider %s" % (method, provider))
        error_counts = {
            'http_timeout':0,
            'content_malformed':0,
            'validation_failed':0,
            'client_server_error':0,
            'rate_limit_reached':0,
            'http_error':0
        }
        success = False
        response = None
        error_limit_reached = False

        while not error_limit_reached and not success and not self.stopped():

            error_type = None
            try:

                if method == 'aliases':
                    if provider.provides_aliases:
                        current_aliases = item.aliases.get_aliases_list(provider.alias_namespaces)
                        if current_aliases:
                            response = provider.aliases(current_aliases)
                        else:
                            logger.debug("processing item: Skipped, no suitable aliases") 
                            response = []
                    else:
                        logger.debug("processing item: Skipped, not implemented") 
                        response = []

                if method == 'metrics':
                    if provider.provides_metrics:
                        current_aliases = item.aliases.get_aliases_list(provider.metric_namespaces)
                        if current_aliases:
                            response = provider.metrics(current_aliases)
                        else:
                            logger.debug("processing item with provider %s: Skipped, no suitable aliases for %s" % (provider, method))
                            response = {}
                    else:
                        logger.debug("processing item with provider %s: Skipped, %s not implemented" % (provider, method))
                        response = {}

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
                logger.error("Error processing item for provider %s: Unknown exception %s, aborting" % (provider, e))
                logger.debug(traceback.format_tb(tb))
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
                        logger.info("Error processing item: %s, error limit reached (%i/%i), aborting" % (
                            error_type, error_counts[error_type], max_retries))
                        error_limit_reached = True
                    else:
                        duration = provider.get_sleep_time(error_type, error_counts[error_type])
                        logger.info("Error processing item, pausing thread for %s" % (error_type, duration))
                        self._interruptable_sleep(duration)
                elif success:
                    logger.info("processing successful")

        return (success, response)


class ProvidersAliasThread(ProviderThread):
    
    def __init__(self, providers, dao):
        self.providers = providers
        queue = AliasQueue(dao)
        ProviderThread.__init__(self, dao, queue)
        self.providers = providers
        self.thread_id = "AliasThread"

    def startup(self):
        # Ensure logs for this thread are marked correctly
        ctxfilter.threadInit()
        ctxfilter.local.backend['method'] = 'alias'
        ctxfilter.local.backend['thread'] = self.thread_id
        
    def process_item(self, item):
        """ Process the given item, obtaining it's metrics.

            This method will retry for the appropriate number of times, sleeping
            if required according to the config settings.
        """
        if not self.stopped():
            for provider in self.providers: 

                ctxfilter.local.backend['provider'] = ':' + provider.provider_name

                (success, response) = self.process_item_for_provider(item, provider, 'aliases')
                if success:
                    # Add in the new aliases to the item
                    # response is a list of (k,v) pairs (may be empty)
                    item.aliases.add_unique(response)
                    item.save()

                else:
                    # This provider has failed and exceeded the 
                    # total number of retries. Don't process any 
                    # more providers, we abort this item entirely

                    # Wipe out the aliases and set last_updated so that the item
                    # is then removed from the queue. If we don't wipe the aliases
                    # then the aliases list is not complete and will given incorrect
                    # results. We had agreed before to go with no results rather than
                    # incorrect.
                    item.aliases.clear_aliases()
                    item.save()
                    break

                #if not self.process_item_for_provider(item, provider, 'biblio'):
                #    # This provider has failed and exceeded the 
                #    # total number of retries. Don't process any 
                #    # more providers, we abort this item entirely
                #    break

            ctxfilter.local.backend['provider'] = ''



class ProviderMetricsThread(ProviderThread):
    """ The provider metrics thread will handle obtaining metrics for all
        requests for a single provider. It will deal with retries and 
        timeouts as required.
    """
    def __init__(self, provider, dao):
        self.provider = provider
        queue = MetricsQueue(dao, provider.provider_name)
        ProviderThread.__init__(self, dao, queue)
        self.thread_id = "MetricsThread:" + str(self.provider.provider_name)

    def startup(self):
        # Ensure logs for this thread are marked correctly
        ctxfilter.threadInit()
        ctxfilter.local.backend['thread'] = self.thread_id
        ctxfilter.local.backend['method'] = 'metric'

    def process_item(self, item):

        (success, metrics) = self.process_item_for_provider(item, 
            self.provider, 'metrics')
        
        ts = str(time.time())

        if success:
            if metrics:
                for key in metrics.keys():
                    item.metrics[key]['values'][ts] = metrics[key]
                    item.metrics[key]['static_meta'] = {} #self.provider
            else:
                # The provider returned None for this item. This is either
                # a non result or a permanent failure
                for key in self.provider.metric_names:
                    item.metrics[key]['values'][ts] = None
                    item.metrics[key]['static_meta'] = {} #self.provider
        else:
            # metrics failed, write None values in for the metric
            # values so we don't attempt to reprocess this item
            for key in self.provider.metric_names:
                item.metrics[key]['values'][ts] = None
                item.metrics[key]['static_meta'] = {} #self.provider
        item.save()
