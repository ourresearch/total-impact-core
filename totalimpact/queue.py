import time
from totalimpact import default_settings
from totalimpact.models import Item, ItemFactory
from totalimpact.pidsupport import StoppableThread, ctxfilter
from totalimpact.providers.provider import ProviderFactory

from totalimpact.tilogging import logging
log = logging.getLogger("queue")

import threading

# some data useful for testing
# d = {"doi" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "url" : ["http://cottagelabs.com"]}

class Queue():
        
    # return next item from this queue (e.g. whatever is on the top of the list)
    # and remove the item from the queue in the process
    def first(self):
        # We catch an exception here, as it's possible the queue is updated in
        # between the call to len and self.queue (and somewhat likely due to 
        # our modes of operation).
        try:
            if len(self.queue) > 0:
                return self.queue[0]
        except IndexError:
            return None
        return None

    # alias should override this
    def add_to_metrics_queues(self, item):
        pass        


class QueueMonitor(StoppableThread):
    """ Worker to watch couch for newly requested items, and place them
        onto the aliases queue. 
    """

    def __init__(self, dao):
        self.dao = dao
        StoppableThread.__init__(self)

    def run(self, runonce=False):
        """ runonce is for the test suite """
        ctxfilter.threadInit()
        ctxfilter.local.backend['thread'] = 'QueueMonitor'

        while not self.stopped():
            viewname = 'queues/requested'
            res = self.dao.view(viewname)

            for res in res["rows"]:
                item_id = res["id"]
                ctxfilter.local.backend['item'] = item_id
                log.info("%20s detected on request queue: item %s" 
                    % ("QueueMonitor", item_id))
                item = ItemFactory.get(self.dao, 
                    item_id, 
                    ProviderFactory.get_provider,
                    default_settings.PROVIDERS)
                # In case clocks are out between processes, use min to ensure queued >= requested
                item.last_queued = max(item.last_requested, time.time()) 

                # Now add the item to the in-memory queue
                AliasQueue.enqueue(item_id)

                # now save back the updated last_queued information
                item.save()
                log.info("%20s saving item %s to update last_queued information" 
                    % ("QueueMonitor", item_id))

            if runonce:
                break
            self._interruptable_sleep(0.5)
    


class AliasQueue(Queue):
    # This is a FIFO queue, add new item ids to the end of this list
    # to queue, remove from the head
    queued_items = []
    queue_lock = threading.Lock()
    
    def __init__(self, dao):
        self.dao = dao

    @classmethod
    def clear(cls):
        """ This is only used from the test suite, normally not needed """
        cls.queued_items = []

    @classmethod
    def enqueue(cls, item_id):
        log.info("%20s enqueuing alias %s"
            % ("AliasQueue", item_id))

        # Synchronised section
        cls.queue_lock.acquire()
        # Add to the end of the queue
        cls.queued_items.append(item_id)
        cls.queue_lock.release()

    def first(self):
        """ Only used in the test suite now """
        self.queue_lock.acquire()
        item_id = None
        if len(self.queued_items) > 0:
            item_id = self.queued_items[0]
        self.queue_lock.release()

        if item_id:
            return ItemFactory.get(self.dao, 
                    item_id, 
			        ProviderFactory.get_provider,
                    default_settings.PROVIDERS)
        else:
            return None

    def dequeue(self):
        # Synchronised section
        self.queue_lock.acquire()
    
        item_id = None
        if len(self.queued_items) > 0:
            # Take from the head of the queue
            item_id = self.queued_items[0]
            log.info("%20s dequeuing item %s from alias" % ("AliasQueue", item_id))
            del self.queued_items[0]

        self.queue_lock.release()

        if item_id:
            return ItemFactory.get(self.dao, 
                item_id, 
                ProviderFactory.get_provider,
                default_settings.PROVIDERS)
        else:
            return None

    def add_to_metrics_queues(self, item):
        # Add the item to the metrics queue
        log.info("%20s adding item %s to metrics queues" 
            % ("AliasQueue", item.id))

        providers_config = default_settings.PROVIDERS
        providers = ProviderFactory.get_providers(providers_config)
        for provider in providers:
            if provider.provides_metrics:
                MetricsQueue.enqueue(item.id, provider.provider_name)


class MetricsQueue(Queue):

    # This is a FIFO queue, add new item ids to the end of this list
    # to queue, remove from the head. For this queue, we have a
    # dictionary as we have a queue per provider
    queued_items = {}
    queue_lock = threading.Lock()
    
    def __init__(self, dao, prov=None):
        self.dao = dao
        self._provider = prov
        if not prov:
            raise ValueError("You must supply a provider name")
        self.init_queue(prov)

    @classmethod
    def clear(cls):
        """ This is only used from the test suite, normally not needed """
        for provider in cls.queued_items.keys():
            cls.queued_items[provider] = []

    @classmethod
    def init_queue(cls, provider):
        if not cls.queued_items.has_key(provider):
            cls.queued_items[provider] = []
        
    @property
    def provider(self):
        return self._provider
        
    @provider.setter
    def provider(self, _provider):
        self._provider = _provider

    @classmethod
    def enqueue(cls, item_id, provider):
        log.info("%20s enqueuing item %s to %s" 
            % ("MetricsQueue", item_id, provider))

        # Synchronised section
        cls.queue_lock.acquire()
        # Add to the end of the queue
        cls.queued_items[provider].append(item_id)
        cls.queue_lock.release()

    def first(self):
        """ Only used in the test suite now """
        self.queue_lock.acquire()
        item_id = None
        if len(self.queued_items[self.provider]) > 0:
            item_id = self.queued_items[self.provider][0]
        self.queue_lock.release()

        if item_id:
            return ItemFactory.get(self.dao, 
                item_id, 
                ProviderFactory.get_provider,
                default_settings.PROVIDERS)
        else:
            return None

    def dequeue(self):
        # Synchronised section
        self.queue_lock.acquire()
    
        item_id = None
        if len(self.queued_items[self.provider]) > 0:
            # Take from the head of the queue
            item_id = self.queued_items[self.provider][0]
            log.info("%20s dequeuing item %s from %s" 
                % ("MetricsQueue", item_id, self.provider))
            del self.queued_items[self.provider][0]

        self.queue_lock.release()

        if item_id:
            return ItemFactory.get(self.dao, 
                item_id, 
                ProviderFactory.get_provider,
                default_settings.PROVIDERS)
        else:
            return None


