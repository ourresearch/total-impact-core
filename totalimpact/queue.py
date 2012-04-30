import time
from totalimpact import default_settings as config
from totalimpact.models import Item, ItemFactory

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)

# some data useful for testing
# d = {"doi" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "url" : ["http://cottagelabs.com"]}


class Queue():
        
    # return next item from this queue (e.g. whatever is on the top of the list)
    # does NOT remove item from tip of queue. To unqueue use save_and_unqueue
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
        
        
class AliasQueue(Queue):
    
    def __init__(self, dao):
        self.dao = dao

    @property
    def queue(self):
        viewname = 'queues/aliases'
        res = self.dao.view(viewname)
        # due to error in couchdb this reads from json output - see dao view

        items = []
        for row in res["rows"]:
            my_item = ItemFactory.get(self.dao, row["id"], config.METRIC_NAMES)
            items.append(my_item)

        return items

    def save_and_unqueue(self, item):
        item.aliases.last_modified = time.time()
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

    @property
    def queue(self):
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
        # due to error in couchdb this reads from json output - see dao view

        items = []
        # using reversed() as a hack...we actually want to use the couchdb
        # descending=true param to get the oldest stuff first, but
        for row in res["rows"]:
            my_item = ItemFactory.get(self.dao, row["id"], config.METRIC_NAMES)
            items.append(my_item)
        return items

