import time
from totalimpact import default_settings
from totalimpact.models import Item, ItemFactory
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
        

######################################################
#
# In-memory queue datastructures
#
# These are used to track the which items in the couchdb views which we have
# already seen, and avoid repeat processing of them. The aliases queue purely
# stores itemid, whereas the metrics queue needs to store (itemid, provider)
# as we do this on a per provider basis
# 

alias_queue_seen = {}
alias_queue_lock = threading.Lock()

metric_queue_seen = {}
metric_queue_lock = threading.Lock()

#######################################################
        

class AliasQueue(Queue):
    
    def __init__(self, dao, queueid=None):
        self.dao = dao
        self.queueid = queueid

    @property
    def queueids(self):
        viewname = 'queues/aliases'
        res = self.dao.view(viewname)
        return [row["id"] for row in res["rows"]]

    @property
    def queue(self):
        # due to error in couchdb this reads from json output - see dao view
        res = self.queueids
        items = []
        for id in res:
            my_item = ItemFactory.get(self.dao, 
		                  id, 
		                  ProviderFactory.get_provider, 
		                  default_settings.PROVIDERS)
            items.append(my_item)

        return items

    def dequeue(self):
        item_ids = self.queueids
        found = None
    
        # Synchronised section
        # This will the the item out of the queue by recording that we
        # have seen the item.
        alias_queue_lock.acquire()

        for item_id in item_ids:
            if not alias_queue_seen.has_key(item_id):
                log.debug("found item %s" % item_id)
                alias_queue_seen[item_id] = True
                found = item_id
                break

        alias_queue_lock.release()

        if found:
            my_item = ItemFactory.get(self.dao, 
                          item_id, 
                          ProviderFactory.get_provider, 
                          default_settings.PROVIDERS)

            return my_item
        else:
            return None

    def save_and_unqueue(self, item):
        item.aliases.last_completed = time.time()
        item.save()

class MetricsQueue(Queue):
    
    def __init__(self, dao, prov=None):
        self.dao = dao
        self._provider = prov
    
    @property
    def provider(self):
        return self._provider
        
    @provider.setter
    def provider(self, _provider):
        self._provider = _provider

    def dequeue(self):
        item_ids = self.queueids
        found = None

        # Synchronised section
        # This will the the item out of the queue by recording that we
        # have seen the item.
        metric_queue_lock.acquire()

        for item_id in item_ids:
            if not metric_queue_seen.has_key((item_id, self.provider)):
                log.debug("found item %s" % item_id)
                metric_queue_seen[(item_id, self.provider)] = True
                found = item_id
                break;

        metric_queue_lock.release()

        if found:
            return ItemFactory.get(self.dao, 
                          item_id, 
                          ProviderFactory.get_provider, 
                          default_settings.PROVIDERS)
        else:
            return None

    @property
    def queueids(self):
        # change this for live
        viewname = 'queues/metrics'
        if self._provider:
            res = self.dao.view(
                viewname,
                startkey=[self.provider,None,None],
                endkey=[self.provider,u'\ufff0',u'\ufff0']
                )
        else:
            res = self.dao.view(viewname)
        return [row["id"] for row in res["rows"]]

    @property
    def queue(self):
        res = self.queueids
        items = []
        # using reversed() as a hack...we actually want to use the couchdb
        # descending=true param to get the oldest stuff first, but
        for id in res:
            my_item = ItemFactory.get(self.dao, 
                          item_id, 
                          ProviderFactory.get_provider, 
                          default_settings.PROVIDERS)
            items.append(my_item)
        return items

    def save_and_unqueue(self, item):
        item.save()

