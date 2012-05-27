#!/usr/bin/env python

import threading, time, sys, copy, datetime, pprint
import traceback
from totalimpact import dao, api
from totalimpact.queue import Queue
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
            thread_count = app.config["PROVIDERS"][provider.provider_name]["workers"]
            logger.info("%20s: spawning, n=%i" % (provider.provider_name, thread_count)) 
            # create and start the metrics threads
            for idx in range(thread_count):
                t = ProviderMetricsThread(provider, self.dao)
                t.thread_id = t.thread_id + '[%i]' % idx
                t.start()
                self.threads.append(t)
        
        logger.info("%20s: spawning" % ("aliases"))
        t = ProvidersAliasThread(self.providers, self.dao)
        t.start()
        self.threads.append(t)

        logger.info("%20s: spawning" % ("monitor_thread"))
        # Start the queue monitor
        # This will watch for newly created items appearing in the couchdb
        # which were requested through the API. It then queues them for the
        # worker processes to handle
        t = QueueMonitor(self.dao)
        t.start()
        t.thread_id = 'monitor_thread'
        self.threads.append(t)
        
    def _monitor(self):        
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
                # just spin our wheels waiting for interrupts
                time.sleep(1)
        except (KeyboardInterrupt, ExitSignal), e:
            pass
    
    def _cleanup(self):
        
        for t in self.threads:
            logger.info("%20s: stopping" % (t.thread_id))
            t.stop()
        for t in self.threads:
            logger.info("%20s: waiting to stop" % (t.thread_id))
            t.join()
            logger.info("%20s: stopped" % (t.thread_id))

        self.threads = []
    



class ProviderThread(StoppableThread):
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
        StoppableThread.__init__(self)
        self.thread_id = "BaseProviderThread"
        self.run_once = False
        self.queue = queue

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
            #logger.debug("%20s: waiting for queue item" % self.thread_id)
            item = self.queue.dequeue()
            
            # Check we have an item, if we have been signalled to stop, then
            # item may be None
            if item:
                logger.debug("%20s: got an item!  dequeued %s" % (self.thread_id, item.id))
                # if we get to here, an item has been popped off the queue and we
                # now want to calculate its metrics. 
                # Repeatedly process this item until we hit the error limit
                # or we successfully process it         
                ctxfilter.local.backend['item'] = item.id
                logger.debug("%20s: processing item %s" % (self.thread_id, item.id))

                # process item saves the item back to the db as necessary
                # also puts alias items on metrics queue when done
                self.process_item(item) 

                ctxfilter.local.backend['item'] = ''

            # Flag for testing. We should finish the run loop as soon
            # as we've processed a single item.
            if run_only_once:
                return

            if not item:
                time.sleep(0.5)



    def call_provider_method(self, 
            provider, 
            method_name, 
            aliases, 
            tiid,
            cache_enabled=True):

        if not aliases:
            logger.debug("%20s: skipping %s %s %s for %s, no aliases" 
                % (self.thread_id, provider, method_name, str(aliases), tiid))
            return None

        provides_method_name = "provides_" + method_name
        provides_method_to_call = getattr(provider, provides_method_name)
        if not provides_method_to_call:
            logger.debug("%20s: skipping %s %s %s for %s, does not provide" 
                % (self.thread_id, provider, method_name, str(aliases), tiid))
            return None

        method_to_call = getattr(provider, method_name)
        if not method_to_call:
            logger.debug("%20s: skipping %s %s %s for %s, no method" 
                % (self.thread_id, provider, method_name, str(aliases), tiid))
            return None

        try:
            override_template_url = api.app.config["PROVIDERS"][provider.provider_name][method_name + "_url"]
        except KeyError:
            # No problem, the provider will use the template_url it knows about
            override_template_url = None

        logger.debug("%20s: calling %s %s for %s" % (self.thread_id, provider, method_name, tiid))
        try:
            response = method_to_call(aliases, override_template_url)
            #logger.debug("%20s: response from %s %s %s for %s, %s" 
            #    % (self.thread_id, provider, method_name, str(aliases), tiid, str(response)))
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

        tiid = item.id
        #logger.debug("%20s: processing %s %s for %s" 
        #    % (self.thread_id, provider, method_name, tiid))
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
                    item.id,
                    cache_enabled=cache_enabled)
                success = True

            except ProviderError, e:
                error_msg = repr(e)

            except Exception, e:
                # All other fatal errors. These are probably some form of
                # logic error. We consider these to be fatal.
                error_msg = repr(e)
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
                logger.debug("%20s: success %s %s for %s, got %i results" 
                    % (self.thread_id, provider, method_name, tiid, len(response)))
            else:
                logger.debug("%20s: success %s %s for %s, got 0 results" 
                    % (self.thread_id, provider, method_name, tiid))

        return (success, response)


class ProvidersAliasThread(ProviderThread):
    
    def __init__(self, providers, dao):
        self.providers = providers
        queue = Queue("aliases")
        ProviderThread.__init__(self, dao, queue)
        self.providers = providers
        self.thread_id = "alias_thread"
        self.dao = dao

    def startup(self):
        # Ensure logs for this thread are marked correctly
        ctxfilter.threadInit()
        ctxfilter.local.backend['method'] = 'alias'
        ctxfilter.local.backend['thread'] = self.thread_id
        
    def process_item(self, item):
        logger.info("%20s: initial alias list for %s is %s" 
                    % (self.thread_id, item.id, item.aliases.get_aliases_list()))

        if not self.stopped():
            for provider in self.providers: 

                ctxfilter.local.backend['provider'] = ':' + provider.provider_name

                (success, new_aliases) = self.process_item_for_provider(item, provider, 'aliases')
                if success:
                    if new_aliases:
                        item.aliases.add_unique(new_aliases)
                else:
                    item.aliases.clear_aliases()
                    logger.info("%20s: NOT SUCCESS in process_item %s clear aliases provider %s" 
                        % (self.thread_id, item.id, provider.provider_name))

                    break

                (success, biblio) = self.process_item_for_provider(item, provider, 'biblio')
                if success:
                    if biblio:
                        # merge old biblio with new, favoring old in cases of conflicts
                        item.biblio = dict(biblio.items() + item.biblio.items())
                        logger.info("%20s: in process_item biblio %s provider %s" 
                            % (self.thread_id, item.id, provider.provider_name))

                else:
                    # This provider has failed and exceeded the 
                    # total number of retries. Don't process any 
                    # more providers, we abort this item entirely
                    break
                logger.info("%20s: interm aliases for item %s after %s: %s" 
                    % (self.thread_id, item.id, provider.provider_name, str(item.aliases.get_aliases_list())))
                logger.info("%20s: interm biblio for item %s after %s: %s" 
                    % (self.thread_id, item.id, provider.provider_name, str(item.biblio)))

            ctxfilter.local.backend['provider'] = ''
            logger.info("%20s: final alias list for %s is %s" 
                    % (self.thread_id, item.id, item.aliases.get_aliases_list()))

            # Time to add this to the metrics queue
            self.queue.add_to_metrics_queues(item)
            logger.info("%20s: FULL ITEM on metrics queue %s %s"
                % (self.thread_id, item.id, pprint.pprint(item.as_dict())))
            logger.debug("%20s: added to metrics queues complete for item %s " % (self.thread_id, item.id))
            self.dao.save(item.as_dict())


    

class ProviderMetricsThread(ProviderThread):
    """ The provider metrics thread will handle obtaining metrics for all
        requests for a single provider. It will deal with retries and 
        timeouts as required.
    """
    def __init__(self, provider, dao):
        self.provider = provider
        queue = Queue(provider.provider_name)
        ProviderThread.__init__(self, dao, queue)
        self.thread_id = self.provider.provider_name + "_thread"
        self.dao = dao

    def startup(self):
        # Ensure logs for this thread are marked correctly
        ctxfilter.threadInit()
        ctxfilter.local.backend['thread'] = self.thread_id
        ctxfilter.local.backend['method'] = 'metric'

    def process_item(self, item):

        (success, metrics) = self.process_item_for_provider(item, 
            self.provider, 'metrics')
        
        if success:
            if metrics:
                for metric_name in metrics.keys():
                    if metrics[metric_name]:
                        snap = {}
                        snap["metric_name"] = metric_name
                        snap["tiid"] = item.id
                        # FIXME when webapp updated to handle it
                        #snap["created"] = datetime.datetime.now().isoformat()
                        snap["created"] = time.time()
                        snap["value"] = metrics[metric_name]
                        snap["drilldown_url"] = "TBD"
                        #print "HERE IS MY SNAP"
                        print snap
                        self.dao.save(snap)





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
    # We need the fiter on the root logger, so that our log settings work,
    # as we're trying to add in thread details to there in the formatter.
    # Without the filter, those details don't exist and logging will fail.
    from totalimpact.backend import ctxfilter
    handler = logging.handlers.RotatingFileHandler(logfile)
    handler.level = logging.ERROR
    formatter = logging.Formatter("%(asctime)s %(levelname)8s %(item)8s %(thread)s%(provider)s - %(message)s")#,"%H:%M:%S,%f")
    handler.formatter = formatter
    handler.addFilter(ctxfilter)
    logger.addHandler(handler)
    ctxfilter.threadInit()

    from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread
    from totalimpact.providers.provider import Provider, ProviderFactory

    # Start all of the backend processes
    providers = ProviderFactory.get_providers(app.config["PROVIDERS"])
    backend = TotalImpactBackend(mydao, providers)
    backend._spawn_threads()
    backend._monitor()
    backend._cleanup()
        
    from totalimpact.queue import Queue
    logger.debug("Items on Queues: %s" 
        % (str([queue_name + " : " + str(Queue.queued_items_ids(queue_name)) for queue_name in Queue.queued_items.keys()]),))

 
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
    

