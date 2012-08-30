import time, datetime, logging, threading, json, copy, couchdb
import newrelic.agent
import rq

from totalimpact import default_settings
from totalimpact.models import ItemFactory
from totalimpact.pidsupport import StoppableThread
from totalimpact.providers.provider import ProviderFactory

log = logging.getLogger("ti.queue")


# some data useful for testing
# d = {"doi" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "url" : ["http://cottagelabs.com"]}

# this is the function currently queued by the api upon create or update item
def update_item(item_doc):
    log.info("IN UPDATE ITEM ******")
    tiQueue.init_queue("aliases")
    tiQueue.enqueue("aliases", item_doc)    

class RQWorker(StoppableThread):
    def __init__(self, myrq):
        log.info("%20s init" % ("RQWorker"))
        self.myrq = myrq
        StoppableThread.__init__(self)

    def run(self):
        log.info("%20s in run" % ("RQWorker"))

        while not self.stopped():
            job = self.myrq.dequeue()
            if job is None:
                self._interruptable_sleep(0.5)
            else:
                log.info('Processing %s from queue %s' % (job.func_name, job.origin))
                job.perform()
                job.delete()

        log.info("%20s shutting down" % ("RQWorker"))   

class CouchWorker(StoppableThread):
    def __init__(self, couch_queue, mydao):
        log.info("%20s init" % ("CouchWorker"))
        self.couch_queue = couch_queue
        self.mydao = mydao
        StoppableThread.__init__(self)

    def run(self):
        log.info("%20s in run" % ("CouchWorker"))

        while not self.stopped():
            doc = self.couch_queue.get()
            if doc is None:
                self._interruptable_sleep(0.5)
            else:
                log.info('Saving doc in CouchWorker!')
                self.mydao.save(doc)
                self.couch_queue.task_done()

        log.info("%20s shutting down" % ("CouchWorker")) 


class tiQueue():
    # This is a FIFO queue, add new item ids to the end of this list
    # to queue, remove from the head
    queued_items = {}
    queue_lock = threading.Lock()
    newrelic_app = newrelic.agent.application('total-impact-core')

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
        cls.newrelic_app.record_metric('Custom/Queue/'+queue_name, 1)

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
            self.newrelic_app.record_metric('Custom/Queue/'+self.queue_name, -1)
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
                tiQueue.enqueue(provider.provider_name, item)

    @property
    def provider(self):
        return self.queue_name



