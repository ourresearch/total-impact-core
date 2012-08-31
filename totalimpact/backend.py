#!/usr/bin/env python
import time, sys, logging, os, traceback, Queue
import rq

from totalimpact import default_settings, dao, tiredis
from totalimpact.tiqueue import tiQueue, RQWorker, CouchWorker
from totalimpact.models import ItemFactory
from totalimpact.pidsupport import StoppableThread
from totalimpact.providers.provider import ProviderError, ProviderFactory

logger = logging.getLogger('ti.backend')
logger.setLevel(logging.DEBUG)


class backendException(Exception):
    pass

class TotalImpactBackend(object):
    
    def __init__(self, dao, myredis, providers):
        self.threads = [] 
        self.dao = dao
        self.myredis = myredis

        self.rq = rq.Queue("alias", connection=myredis)
        self.dao.update_design_doc()
        self.providers = providers
        self.couch_queue = Queue.Queue()

    def run(self):
        self._spawn_threads()
        try:
            self._monitor()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Interrupted ... exiting ...")
            self._cleanup()

    def _get_num_workers_from_config(self, provider_name, provider_config):
        relevant_provider_config = {"workers":1}
        for (key, provider_config_dict) in provider_config:
            if (key==provider_name):
                relevant_provider_config = provider_config_dict
        return relevant_provider_config["workers"]

    def _spawn_threads(self):
        
        for provider in self.providers:
            if not provider.provides_metrics:                            
                continue

            thread_count = self._get_num_workers_from_config(
                provider.provider_name, 
                default_settings.PROVIDERS)

            logger.info("%20s: spawning, n=%i" % (provider.provider_name, thread_count)) 
            # create and start the metrics threads
            for idx in range(thread_count):
                t = ProviderMetricsThread(self.couch_queue, self.dao, self.myredis, provider)
                t.thread_id = t.thread_id + '[%i]' % idx
                t.start()
                self.threads.append(t)
        
        logger.info("%20s: spawning" % ("aliases"))
        t = ProvidersAliasThread(self.couch_queue, self.dao, self.myredis, self.providers)
        t.start()
        self.threads.append(t)

        logger.info("%20s: spawning" % ("RQ_monitor_thread"))
        # Start the RQ queue monitor
        # This will watch for newly created items appearing in the couchdb
        # which were requested through the API. It then queues them for the
        # worker processes to handle
        t = RQWorker(self.rq)
        t.start()
        t.thread_id = 'RQWorker_thread'
        self.threads.append(t)        

        t = CouchWorker(self.couch_queue, self.dao)
        t.start()
        t.thread_id = 'CouchWorker_thread'
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


    def __init__(self, dao, myredis, queue):
        self.dao = dao
        self.myredis = myredis
        StoppableThread.__init__(self)
        self.thread_id = "BaseProviderThread"
        self.run_once = False
        self.queue = queue

    def log_error(self, item, error_msg, tb):
        # This method is called to record any errors which we obtain when
        # trying process an item.
        logger.error("exception for item(%s): %s" % (item["_id"], error_msg))
        
        e = backendException(error_msg)
        e.id = item["_id"]
        e.provider = self.thread_id
        e.stack_trace = "".join(traceback.format_tb(tb))
        
        logger.debug(str(e.stack_trace))
        

    def run(self, run_only_once=False):

        while not self.stopped():
            # get the first item on the queue - this waits until
            # there is something to return
            #logger.debug("%20s: waiting for queue item" % self.thread_id)
            item = self.queue.dequeue()
            
            # Check we have an item, if we have been signalled to stop, then
            # item may be None
            if item:
                logger.debug("%20s: got an item!  dequeued %s" % (self.thread_id, item["_id"]))
                # if we get to here, an item has been popped off the queue and we
                # now want to calculate its metrics. 
                # Repeatedly process this item until we hit the error limit
                # or we successfully process it         
                logger.debug("%20s: processing item %s" % (self.thread_id, item["_id"]))

                # process item saves the item back to the db as necessary
                # also puts alias items on metrics queue when done
                self.process_item(item) 


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
            logger.debug("%20s: %20s skipping %s for %s, no aliases" 
                % (self.thread_id, provider, method_name, tiid))
            return None

        provides_method_name = "provides_" + method_name
        print provider
        print provides_method_name
        provides_method_to_call = getattr(provider, provides_method_name)
        if not provides_method_to_call:

            if method_name == "metrics":
                # we're not going to call this method, so decr the counter
                provider_name =  provider.__class__.__name__
                self.myredis.decr_num_providers_left(tiid, provider_name)

            #logger.debug("%20s: %20s skipping %s for %s, does not provide" 
            #    % (self.thread_id, provider, method_name, tiid))
            return None

        method_to_call = getattr(provider, method_name)
        if not method_to_call:
            #logger.debug("%20s: %20s skipping %s for %s, no method" 
            #    % (self.thread_id, provider, method_name, tiid))
            return None

        #logger.debug("%20s: %20s calling %s for %s" % (self.thread_id, provider, method_name, tiid))
        try:
            response = method_to_call(aliases)
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

        tiid = item["_id"]
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

                if not cache_enabled:
                    logger.debug("%20s: cache NOT enabled %s %s for %s"
                        % (self.thread_id, provider, method_name, tiid))

                # convert the dict into a list of (namespace, id) tuples, like:
                # [(doi, 10.123), (doi, 10.345), (pmid, 1234567)]
                alias_tuples = []
                for ns, ids in item["aliases"].iteritems():
                    if isinstance(ids, basestring): # it's a date, not a list of ids
                        alias_tuples.append((ns, ids))
                    else:
                        for id in ids:
                            alias_tuples.append((ns, id))


                response = self.call_provider_method(
                    provider, 
                    method_name, 
                    alias_tuples,
                    item["_id"],
                    cache_enabled=cache_enabled)
                success = True

            except ProviderError, e:
                error_msg = repr(e)
                logger.info('ProviderError on %s %s' % (provider, method_name))

            except Exception, e:
                # All other fatal errors. These are probably some form of
                # logic error. We consider these to be fatal.
                error_msg = repr(e)
                error_limit_reached = True
                tb = sys.exc_info()[2]
                self.log_error(item, '%s on %s %s' % (error_msg, provider, method_name), tb)

            if error_msg:
                # If we had any errors, update the error counts and sleep if 
                # we need to do so, before retrying. 
                error_counts += 1

                if ((error_counts > max_retries) and (max_retries != -1)):
                    logger.error("process_item_for_provider: error limit reached (%i/%i) for %s, aborting %s %s" % (
                        error_counts, max_retries, item["_id"], provider, method_name))
                    error_limit_reached = True
                else:
                    duration = provider.get_sleep_time(error_counts)
                    logger.warning("process_item_for_provider: error, pausing thread for %i %s %s, %s" % (duration, item["_id"], provider, method_name))
                    self._interruptable_sleep(duration)                

        if success:
            # response may be None for some methods and inputs
            if response:
                logger.debug("%20s: %20s success %s for %s, got %i results" 
                    % (self.thread_id, provider, method_name, tiid, len(response)))
            else:
                logger.debug("%20s: %20s success %s for %s, got 0 results" 
                    % (self.thread_id, provider, method_name, tiid))

        return (success, response)


class ProvidersAliasThread(ProviderThread):
    
    def __init__(self, couch_queue=None, dao=None, myredis=None, providers=None):
        self.providers = providers
        queue = tiQueue("aliases")
        ProviderThread.__init__(self, dao, myredis, queue)
        self.providers = providers

        self.thread_id = "alias_thread"
        self.worker_id = "alias_thread"
        self.dao = dao
        self.couch_queue = couch_queue
        self.method_name = "aliases"
        self.provider_name = "aliases"

    def update_loop(self, item):
        logger.info("%20s: initial alias list for %s is %s" 
                    % (self.worker_id, item["_id"], item["aliases"]))

        new_aliases = item["aliases"]
        tiid = item["_id"]
        all_new_aliases = []
        while (new_aliases):
            (success, new_aliases) = self.ask_provider(item["aliases"], item["_id"])
            if success:
                if new_aliases:
                    logger.debug("here are the new aliases: {aliases}.".format(
                        aliases=str(new_aliases)))
                    all_new_aliases += new_aliases

                    #remove title and url new aliases to determine loop
                    new_aliases = [(namespace, nid) for (namespace, nid) in new_aliases if namespace not in ["url", "title"]]
            else:
                logger.info("%20s: NOT SUCCESS in update_looop %s, partial aliases only for provider %s"
                    % (self.worker_id, item["_id"], self.provider_name))

        if all_new_aliases:
            item = self.add_aliases(all_new_aliases, item) # to be replaced

        logger.info("%20s: final alias list for %s is %s" 
                % (self.thread_id, item["_id"], item["aliases"]))

        # Time to add this to the metrics queue
        logger.debug("%20s: FULL ITEM on metrics queue %s %s"
            % (self.thread_id, item["_id"], item))
        logger.debug("%20s: added to metrics queues complete for item %s " % (self.thread_id, item["_id"]))
        if self.couch_queue:
            self.couch_queue.put(("alias", item))
        self.queue.add_to_metrics_queues(item)

        return all_new_aliases


    def update(self, item):
        logger.info("%20s: initial alias list for %s is %s" 
                    % (self.worker_id, item["_id"], item["aliases"]))

        (success, new_aliases) = self.ask_provider(item["aliases"], item["_id"])

        if success:
            if new_aliases:
                logger.debug("here are the new aliases from {provider}: {aliases}.".format(
                    provider=self.provider_name, aliases=str(new_aliases)))
                item = self.add_aliases(new_aliases, item)
        else:
            logger.info("%20s: NOT SUCCESS in update %s, partial aliases only for provider %s"
                % (self.worker_id, item["_id"], self.provider_name))

        logger.info("%20s: interm aliases for item %s after %s: %s"
            % (self.worker_id, item["_id"],  self.provider_name, str(item["aliases"])))

        return item

    def add_aliases(self, new_alias_tuples, item):
        for ns, nid in new_alias_tuples:
            try:
                item["aliases"][ns].append(nid)
                item["aliases"][ns] = list(set(item["aliases"][ns]))
            except KeyError: # no ids for that namespace yet. make it.
                item["aliases"][ns] = [nid]
            except AttributeError:
                # nid is a string; overwrite.
                item["aliases"][ns] = nid
                logger.debug("aliases[{ns}] is a string ('{nid}'); overwriting".format(
                    ns=ns, nid=nid))
        return item

    def alias_tuples_from_dict(self, aliases_dict):
        """
        Convert from aliases dict we use in items, to a list of alias tuples.

        The providers need the tuples list, which look like this:
        [(doi, 10.123), (doi, 10.345), (pmid, 1234567)]
        """
        alias_tuples = []
        for ns, ids in aliases_dict.iteritems():
            if isinstance(ids, basestring): # it's a date, not a list of ids
                alias_tuples.append((ns, ids))
            else:
                for id in ids:
                    alias_tuples.append((ns, id))

        return alias_tuples

    def log_error(self, aliases, tiid, error_msg, tb):
        # This method is called to record any errors which we obtain when
        # trying to call the provider.
        logger.error("%20s: exception for item(%s): %s" %
                     (self.worker_id, tiid, error_msg))
        
        e = backendException(error_msg)
        e.id = tiid
        e.provider = self.provider_name
        e.stack_trace = "".join(traceback.format_tb(tb))
        
        logger.debug(str(e.stack_trace))

    def decide_provider_to_call(self, alias_dict):
        '''Uses available aliases to decide the item's genre'''

        provider_name = None
        if "doi" in alias_dict:
            if "10.5061/dryad." in "".join(alias_dict["doi"]):
                provider_name = "dryad"
            else:
                provider_name = "crossref"
        elif "pmid" in alias_dict:
            provider_name = "pubmed"
        elif "url" in alias_dict:
            joined_urls = "".join(alias_dict["url"])
            if "slideshare.net" in joined_urls:
                provider_name = "slideshare"
            elif "github.com" in joined_urls:
                provider_name = "github"
        if "title" in alias_dict:
            provider_name = None
        return provider_name


    def ask_provider(self, aliases, tiid):
        """ Get a response from the provider, using the supplied aliases

            This will deal with retries and sleep / backoff as per the
            configuration for the given provider.  Should
            probably be split into smaller methods; some of these should be
            in the ItemFactory.
        """

        error_counts = 0
        success = False
        error_limit_reached = False
        error_msg = False
        max_retries = 0
        response = None

        while not error_limit_reached and not success:
            response = None

            try:
                cache_enabled = (error_counts == 0)

                if not cache_enabled:
                    logger.debug("%20s: cache NOT enabled %s for %s"
                        % (self.worker_id, self.method_name, tiid))

                provider_name = self.decide_provider_to_call(aliases)
                if provider_name:
                    provider = ProviderFactory.get_provider(provider_name)
                else:
                    provider = None

                alias_tuples = self.alias_tuples_from_dict(aliases)
                if alias_tuples and provider:
                    logger.debug("%20s: calling %s for %s" %
                                 (self.worker_id, self.method_name, tiid))
                    try:
                        response = self.call_provider_method(
                            provider, 
                            self.method_name, 
                            alias_tuples,
                            tiid,
                            cache_enabled=cache_enabled)
                    except NotImplementedError:
                        response = None
                else:
                    logger.debug("%20s: skipping %s %s %s for %s, no aliases"
                        % (self.worker_id, self.provider_name, self.method_name, str(aliases), tiid))
                    response = None

                success = True # didn't get any errors.

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
                self.log_error(
                    aliases,
                    tiid,
                    '%s on %s %s' % (error_msg, self.provider_name, self.method_name),
                    tb)

                error_counts += 1

                if error_counts > max_retries:
                    logger.error("%20s: error limit reached (%i/%i) for %s, aborting %s %s" % (
                        self.worker_id, error_counts, max_retries, tiid, self.provider_name, self.method_name))
                    error_limit_reached = True
                else:
                    duration = self.provider.get_sleep_time(error_counts)
                    logger.warning("%20s: error on %s, pausing thread for %i seconds." %
                        (self.worker_id, tiid, duration))
                    time.sleep(duration)

        if success:
            # response may be None for some methods and inputs
            if response:
                logger.debug("%20s: success %s %s for %s, got %i results"
                    % (self.worker_id, self.provider_name, self.method_name, tiid, len(response)))
            else:
                logger.debug("%20s: success %s %s for %s, got 0 results"
                    % (self.worker_id, self.provider_name, self.method_name, tiid))

        return (success, response)



    def process_item(self, item):
        return self.update_loop(item)

    

class ProviderMetricsThread(ProviderThread):
    """ The provider metrics thread will handle obtaining metrics for all
        requests for a single provider. It will deal with retries and 
        timeouts as required.
    """
    def __init__(self, couch_queue, dao, myredis, provider):
        self.provider = provider
        queue = tiQueue(provider.provider_name)
        ProviderThread.__init__(self, dao, myredis, queue)
        self.thread_id = self.provider.provider_name + "_thread"
        self.dao = dao
        self.myredis = myredis
        self.couch_queue = couch_queue


    def process_item(self, item):
        # used by logging

        try:
            (success, metrics) = self.process_item_for_provider(item, 
                self.provider, 'metrics')

            if success:
                if metrics:
                    for metric_name in metrics.keys():
                        if metrics[metric_name]:
                            snap = ItemFactory.build_snap(item["_id"], metrics[metric_name], metric_name)
                            self.couch_queue.put(("snap", snap))
        except ProviderError:
            pass
        finally:
            # update provider counter so api knows when all have finished
            provider_name =  self.provider.__class__.__name__
            self.myredis.decr_num_providers_left(item["_id"], provider_name)


def main():
    mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.environ["CLOUDANT_DB"])
    myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))

    # Start all of the backend processes
    providers = ProviderFactory.get_providers(default_settings.PROVIDERS)
    backend = TotalImpactBackend(mydao, myredis, providers)
    backend._spawn_threads()
    backend._monitor()
    backend._cleanup()
        
    logger.debug("Items on tiQueues: %s" 
        % (str([queue_name + " : " + str(tiQueue.queued_items_ids(queue_name)) for queue_name in tiQueue.queued_items.keys()]),))

 
if __name__ == "__main__":
    main()
    

