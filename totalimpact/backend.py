#!/usr/bin/env python

import threading, time, sys
import traceback
from totalimpact.config import Configuration
from totalimpact import dao, api
from totalimpact.queue import AliasQueue, MetricsQueue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.models import Error
from totalimpact.pidsupport import StoppableThread, ctxfilter

from totalimpact.tilogging import logging

from totalimpact.providers.provider import ProviderConfigurationError, ProviderTimeout, ProviderHttpError
from totalimpact.providers.provider import ProviderClientError, ProviderServerError, ProviderContentMalformedError
from totalimpact.providers.provider import ProviderValidationFailedError, ProviderRateLimitError
from totalimpact.providers.provider import ProviderError

import daemon
import lockfile
from totalimpact.pidsupport import PidFile

from optparse import OptionParser
import os

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
            logger.info("Interrupted ... exiting ...")
            self._cleanup()
    
    def _spawn_threads(self):
        
        for provider in self.providers:
            if not provider.provides_metrics:
                continue
            logger.info("Spawning thread for provider " + str(provider.provider_name))
            # create and start the metrics threads
            t = ProviderMetricsThread(provider, self.dao)
            t.start()
            self.threads.append(t)
        
        logger.info("Spawning thread for aliases")
        alias_thread = ProvidersAliasThread(self.providers, self.dao)
        alias_thread.start()
        self.threads.append(alias_thread)
        
    def _monitor(self):        
        while True:
            # just spin our wheels waiting for interrupts
            time.sleep(1)
    
    def _cleanup(self):
        for t in self.threads:
            logger.info("Stopping " + t.thread_id)
            t.stop()
            t.join()
            logger.info("... stopped")
        self.threads = []
    


class QueueConsumer(StoppableThread):
    
    thread_id = 'Queue Consumer'

    def __init__(self, queue):
        StoppableThread.__init__(self)
        self.queue = queue

    def first(self):
        item = None
        while item is None and not self.stopped():
            item = self.queue.first()
            if item is None:
                # if the queue is empty, wait 0.5 seconds before checking
                # again
                time.sleep(0.5)
        return item
        
    def dequeue(self):
        # get the first item on the queue (waiting until there is
        # such a thing if necessary)
        item = None
        while item is None and not self.stopped():
            item = self.queue.dequeue()
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

    def log_error(self, item, error_msg, tb):
        # This method is called to record any errors which we obtain when
        # trying process an item.
        logger.error("exception for item(%s): %s" % (item.id, error_msg))
        
        e = Error()
        e.message = error_msg
        e.id = item.id
        e.provider = self.thread_id
        e.stack_trace = "".join(traceback.format_tb(tb))
        
        logger.debug(str(e.stack_trace))
        

    def startup(self):
        # Ensure logs for this thread are marked correctly
        ctxfilter.threadInit()

    def run(self, run_only_once=False):
        self.startup()

        while not self.stopped():
            # get the first item on the queue - this waits until
            # there is something to return
            logger.debug("%s - waiting for queue item" % self.thread_id)
            item = self.dequeue()
            
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
                logger.debug("item unqueued")
                ctxfilter.local.backend['item'] = ''

            # Flag for testing. We should finish the run loop as soon
            # as we've processed a single item.
            if run_only_once:
                return

    def call_provider_method(self, 
            provider, 
            method_name, 
            aliases, 
            cache_enabled=True):

        logger.info("call_provider_method %s %s %s" % (provider, method_name, str(aliases)))

        if not aliases:
            logger.debug("Skipping item with provider %s: Missing aliases for %s" % (provider, method_name))
            return None

        method_to_call = getattr(provider, method_name)
        if not method_to_call:
            logger.debug("Skipping item with provider %s: Missing method for %s" % (provider, method_name))
            return None

        try:
            override_template_url = api.app.config["PROVIDERS"][provider.provider_name][method_name + "_url"]
        except KeyError:
            # No problem, the provider will use the template_url it knows about
            override_template_url = None

        logger.info("CALLING %s %s with aliases %s" % (provider, method_name, str(aliases)))
        try:
            response = method_to_call(aliases, override_template_url)
            logger.info("finished CALLING %s %s with aliases %s" % (provider, method_name, str(aliases)))
            logger.info("response: %s" %(str(response)))
        except NotImplementedError:
            response = None
        return response


    def process_item_for_provider(self, item, provider, method_name):
        """ Run the given method for the given provider on the given item
            This will deal with retries and sleep / backoff as per the 
            configuration for the given provider. We will return true if
            the given method passes, or if it is not implemented.
        """
        if method_name not in ('aliases', 'biblio', 'metrics'):
            raise NotImplementedError("Unknown method %s for provider class" % method_name)
        
        logger.info("processing %s for provider %s" % (method_name, provider))
        error_counts = 0
        success = False
        error_limit_reached = False
        error_msg = False
        max_retries = provider.get_max_retries()
        response = None

        while not error_limit_reached and not success and not self.stopped():
            response = None

            try:
                cache_enabled = (error_counts == 0)

                response = self.call_provider_method(
                    provider, 
                    method_name, 
                    item.aliases.get_aliases_list(), 
                    cache_enabled=cache_enabled)
                success = True

            except ProviderError, e:
                error_msg = str(e)

            except Exception, e:
                # All other fatal errors. These are probably some form of
                # logic error. We consider these to be fatal.
                error_msg = "unknown error"
                logger.error("process_item_for_provider %s %s %s: Unknown exception %s, aborting" % (item.id, provider, method_name, e))
                tb = sys.exc_info()[2]
                logger.debug(traceback.format_tb(tb))
                error_limit_reached = True

            if error_msg:
                # If we had any errors, update the error counts and sleep if 
                # we need to do so, before retrying. 
                tb = sys.exc_info()[2]
                self.log_error(item, '%s on %s %s' % (error_msg, provider, method_name), tb)

                error_counts += 1

                if ((error_counts > max_retries) and (max_retries != -1)):
                    logger.error("process_item_for_provider: error limit reached (%i/%i) for %s, aborting %s %s" % (
                        error_counts, max_retries, item.id, provider, method_name))
                    error_limit_reached = True
                else:
                    duration = provider.get_sleep_time(error_counts)
                    logger.warning("process_item_for_provider: error, pausing thread for %i %s %s, %s" % (duration, item.id, provider, method_name))
                    self._interruptable_sleep(duration)                

        if success:
            # response may be None for some methods and inputs
            if response:
                logger.info("processing %s %s %s successful, got %i results" % (item.id, provider, method_name, len(response)))
            else:
                logger.info("processing %s %s %s successful, got 0 results" % (item.id, provider, method_name))

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
        if not self.stopped():
            for provider in self.providers: 

                ctxfilter.local.backend['provider'] = ':' + provider.provider_name

                (success, new_aliases) = self.process_item_for_provider(item, provider, 'aliases')
                if success:
                    if new_aliases:
                        item.aliases.add_unique(new_aliases)
                    item.save()

                else:
                    # This provider has failed and exceeded the 
                    # total number of retries. Don't process any 
                    # more providers, we abort this item entirely

                    # Wipe out the aliases and set last_modified so that the item
                    # is then removed from the queue. If we don't wipe the aliases
                    # then the aliases list is not complete and will given incorrect
                    # results. We'd rather have no results rather than
                    # incorrect.
                    item.aliases.clear_aliases()
                    item.save()
                    break

                (success, biblio) = self.process_item_for_provider(item, provider, 'biblio')
                if success:
                    if biblio:
                        for key in biblio.keys():
                            if not item.biblio.has_key('data'):
                                item.biblio['data'] = {}
                            item.biblio['data'][key] = biblio[key]
                else:
                    # This provider has failed and exceeded the 
                    # total number of retries. Don't process any 
                    # more providers, we abort this item entirely
                    break

            ctxfilter.local.backend['provider'] = ''
            logger.info("final alias list is %s" % item.aliases.get_aliases_list())

        



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
                    if not item.metrics.has_key(key):
                        item.metrics[key] = {}
                        item.metrics[key]['values'] = {}
                    item.metrics[key]['values'][ts] = metrics[key]
                    item.metrics[key]['static_meta'] = {} #self.provider
            else:
                # The provider returned None for this item. This is either
                # a non result or a permanent failure
                for key in self.provider.metric_names:
                    if not item.metrics.has_key(key):
                        item.metrics[key] = {}
                        item.metrics[key]['values'] = {}
                    item.metrics[key]['values'][ts] = None
                    item.metrics[key]['static_meta'] = {} #self.provider
        else:
            # metrics failed, write None values in for the metric
            # values so we don't attempt to reprocess this item
            for key in self.provider.metric_names:
                if not item.metrics.has_key(key):
                    item.metrics[key] = {}
                    item.metrics[key]['values'] = {}
                item.metrics[key]['values'][ts] = None
                item.metrics[key]['static_meta'] = {} #self.provider
        item.save()



from totalimpact import dao
from totalimpact.models import Item, Collection, ItemFactory, CollectionFactory
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.queue import QueueMonitor
from totalimpact.tilogging import logging
from totalimpact import default_settings
from totalimpact.api import app


def main(logfile=None):

    logger = logging.getLogger()

    mydao = dao.Dao(
        app.config["DB_NAME"],
        app.config["DB_URL"],
        app.config["DB_USERNAME"],
        app.config["DB_PASSWORD"]
    ) 

    # Adding this by handle. fileConfig doesn't allow filters to be added
    from totalimpact.backend import ctxfilter
    handler = logging.handlers.RotatingFileHandler(logfile)
    handler.level = logging.DEBUG
    formatter = logging.Formatter("%(asctime)s %(levelname)8s %(item)8s %(thread)s%(provider)s - %(message)s")#,"%H:%M:%S,%f")
    handler.formatter = formatter
    handler.addFilter(ctxfilter)
    logger.addHandler(handler)
    ctxfilter.threadInit()

    logger.debug("test")

    from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
    from totalimpact.providers.provider import Provider, ProviderFactory

    # Start all of the backend processes
    print "Starting alias retrieval thread"
    providers = ProviderFactory.get_providers(app.config["PROVIDERS"])

    # Start the queue monitor
    # This will watch for newly created items appearing in the couchdb
    # which were requested through the API. It then queues them for the
    # worker processes to handle
    qm = QueueMonitor(mydao)
    qm.start()

    alias_threads = []
    thread_count = app.config["ALIASES"]["workers"]
    for idx in range(thread_count):
        at = ProvidersAliasThread(providers, mydao)
        at.thread_id = 'AliasThread(%i)' % idx
        at.start()
        alias_threads.append(at)

    print "Starting metric retrieval threads..."
    # Start each of the metric providers
    metrics_threads = []
    for provider in providers:
        thread_count = app.config["PROVIDERS"][provider.provider_name]["workers"]
        print "  ", provider.provider_name
        for idx in range(thread_count):
            thread = ProviderMetricsThread(provider, mydao)
            metrics_threads.append(thread)
            thread.thread_id = thread.thread_id + '(%i)' % idx
            thread.start()

    # Install a signal handler so we'll break out of the main loop
    # on receipt of relevant signals
    class ExitSignal(Exception):
        pass
 
    def kill_handler(signum, frame):
        raise ExitSignal()

    import signal
    signal.signal(signal.SIGTERM, kill_handler)

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, ExitSignal), e:
        pass

    from totalimpact.queue import AliasQueue
    from totalimpact.queue import MetricsQueue
    print "Items on Alias Queue:", AliasQueue.queued_items
    print "Items on Metrics Queue:", MetricsQueue.queued_items

    print "Stopping queue monitor"
    qm.stop()
    print "Waiting on queue monitor"
    qm.join()

    print "Stopping alias threads"
    for at in alias_threads:
        at.stop()
    print "Stopping metric threads"
    for thread in metrics_threads:
        thread.stop()
    print "Waiting on metric threads"
    for thread in metrics_threads:
        thread.join()
    print "Waiting on alias thread"
    for at in alias_threads:
        at.join()
    print "All stopped"

 
if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("-p", "--pid",
                      action="store", dest="pid", default=None,
                      help="pid file")
    parser.add_option("-s", "--startup-log",
                      action="store", dest="startup_log", default=None,
                      help="startup log")
    parser.add_option("-l", "--log",
                      action="store", dest="log", default=None,
                      help="runtime log")
    parser.add_option("-d", "--daemon",
                      action="store_true", dest="daemon", default=False,
                      help="run as a daemon")

    (options, args) = parser.parse_args()
    # Root of the totalimpact directory
    rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    if options.log:
        logfile = options.log
    else:
        logfile = os.path.join(rootdir, 'logs', 'backend.log')

    if options.daemon:
        context = daemon.DaemonContext()

        if options.startup_log:
            output = open(options.startup_log,'a+')
        else:
            output = open(os.path.join(rootdir, 'logs', 'backend-startup.log'),'a+')

        context.stderr = output
        context.stdout = output
        if options.pid:
            context.pidfile = PidFile(options.pid)
        else: 
            context.pidfile = PidFile(os.path.join(rootdir, 'run', 'backend.pid'))
        context.working_directory = rootdir
        with context:
            main(logfile)

    else:
        main(logfile)
    

