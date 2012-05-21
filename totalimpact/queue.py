import time
from totalimpact import default_settings
from totalimpact.models import Item, ItemFactory
from totalimpact.pidsupport import StoppableThread, ctxfilter
from totalimpact.providers.provider import ProviderFactory

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)

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

    # implement this in inheriting classes if needs to be different
    # Saving the item should solve this for now, as the providers are meant
    # to update their last_modified as appropriate.
    def save_and_unqueue(self, item):
        item.save()
        

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
                log.info("Item Requsted")
                item = ItemFactory.get(self.dao, 
                    item_id, 
                    ProviderFactory.get_provider,
                    default_settings.PROVIDERS)
                # In case clocks are out between processes, use min to ensure queued >= requested
                item.last_queued = max(item.last_requested, time.time()) 
                item.save()
                # Now add the item to the in-memory queue
                AliasQueue.enqueue(item_id)

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
            log.debug("found item %s" % item_id)
            del self.queued_items[0]

        self.queue_lock.release()

        if item_id:
            return ItemFactory.get(self.dao, 
                item_id, 
                ProviderFactory.get_provider,
                default_settings.PROVIDERS)
        else:
            return None

    def save_and_unqueue(self, item):
        # Add the item to the metrics queue
        from totalimpact.api import app
        providers = app.config["PROVIDERS"].keys()
        for provider in providers:
            MetricsQueue.enqueue(item.id, provider)
        item.save()


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
            log.debug("found item %s" % item_id)
            del self.queued_items[self.provider][0]

        self.queue_lock.release()

        if item_id:
            return ItemFactory.get(self.dao, 
                item_id, 
                ProviderFactory.get_provider,
                default_settings.PROVIDERS)
        else:
            return None

    def save_and_unqueue(self, item):
        item.save()
    

