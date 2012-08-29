import time, datetime, logging, threading, simplejson, copy, couchdb
import newrelic.agent

from totalimpact import default_settings
from totalimpact.models import ItemFactory
from totalimpact.pidsupport import StoppableThread
from totalimpact.providers.provider import ProviderFactory

log = logging.getLogger("ti.queue")


# some data useful for testing
# d = {"doi" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "url" : ["http://cottagelabs.com"]}


class QueueMonitor(StoppableThread):
    """ Worker to watch couch for items that need aliases (new or update)
        and place them onto the aliases in-memory queue. 
    """

    def __init__(self, dao):
        self.dao = dao
        StoppableThread.__init__(self)

    def run(self, runonce=False):
        """ runonce is for the test suite """

        error_count = 0
        while not self.stopped():
            viewname = 'queues/needs_aliases'
            res = self.dao.view(viewname)

            try:
                rows = res.rows
            except couchdb.ResourceNotFound:
                log.warning("%20s can't find database. Sleeping then will try again" 
                    % ("QueueMonitor"))
                time.sleep(0.5)
                continue

            except couchdb.ServerError, e:
                log.error("The QueueMonitor got a server error back from CouchDB:{str}".format(
                    str=e.__repr__()
                ))
                error_count += 1
                if error_count > 3:
                    log.critical("QueueMonitor still getting CouchDB server errors after {tries} tries: {error_str}".format(
                        tries=error_count,
                        error_str=e.__repr__()
                    ))

                time.sleep(2**error_count)
                continue


            error_count = 0
            for row in rows:
                item = copy.deepcopy(row["value"])

                log.info("%20s detected on request queue: item %s"
                    % ("QueueMonitor", item["_id"]))

                # now save back the updated needs_aliases information
                # do this before putting on queue, so that no one has changed it.
                log.info("%20s UPDATING needs_aliases date in db: item %s" 
                    % ("QueueMonitor", item["_id"]))

                # remove the needs_aliases key from doc, to take off queue
                del item["needs_aliases"]

                self.dao.save(item)

                # Now add the item to the in-memory queue
                Queue.init_queue("aliases")
                Queue.enqueue("aliases", item)

            if runonce:
                break
            self._interruptable_sleep(0.5)
    
class Queue():
    # This is a FIFO queue, add new item ids to the end of this list
    # to queue, remove from the head
    queued_items = {}
    queue_lock = threading.Lock()
    

    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.init_queue(queue_name)

    @classmethod
    def clear(cls):
        """ This is only used from the test suite, normally not needed """
        for queue_name in cls.queued_items.keys():
            cls.queued_items[queue_name] = []

    @classmethod
    def init_queue(cls, queue_name):
        if not cls.queued_items.has_key(queue_name):
            cls.queued_items[queue_name] = []

    @classmethod
    def queued_items_ids(cls, queue_name):
        return ([item["_id"] for item in cls.queued_items[queue_name]])

    @classmethod
    def enqueue(cls, queue_name, item):
        log.info("%20s enqueuing item %s"
            % ("Queue " + queue_name, item["_id"]))
        newrelic.agent.record_custom_metric('Custom/queue:'+queue_name, 1)

        # Synchronised section
        cls.queue_lock.acquire()
        # Add to the end of the queue
        cls.queued_items[queue_name].append(copy.deepcopy(item))
        cls.queue_lock.release()


    def dequeue(self):
        # Synchronised section
        item = None
        self.queue_lock.acquire()
        if len(self.queued_items[self.queue_name]) > 0:
            # Take from the head of the queue
            item = copy.deepcopy(self.queued_items[self.queue_name][0])
            log.info("%20s  dequeuing item %s" 
                % ("Queue " + self.queue_name, item["_id"]))
            del self.queued_items[self.queue_name][0]
            newrelic.agent.record_custom_metric('Custom/queue:'+self.queue_name, -1)
        self.queue_lock.release()
        return item

    @classmethod
    def add_to_metrics_queues(self, item):
        # Add the item to the metrics queue
        log.info("%20s  adding item %s to all metrics queues" 
            % ("Queue", item["_id"]))

        providers_config = default_settings.PROVIDERS
        providers = ProviderFactory.get_providers(providers_config)
        for provider in providers:
            if provider.provides_metrics:
                Queue.enqueue(provider.provider_name, item)

    @property
    def provider(self):
        return self.queue_name



