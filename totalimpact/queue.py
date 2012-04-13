import time

from totalimpact.models import Item

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)

# some data useful for testing
# d = {"doi" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "url" : ["http://cottagelabs.com"]}


class Queue():
        
    # TODO: 
    # return next item from this queue (e.g. whatever is on the top of the list
    # does NOT remove item from tip of queue
    def first(self):
        if len(self.queue) > 0:
            return self.queue[0]
        else:
            return None
        #return Item(**{'_rev': '4-a3e3574c44c95b86bb2247fe49e171c8', '_id': 'test', '_deleted_conflicts': ['3-2b27cebd890ff56e616f3d7dadc69c74'], 'hello': 'world', 'aliases': {'url': ['http://cottagelabs.com'], 'doi': ['10.1371/journal.pcbi.1000361', "10.1016/j.meegid.2011.02.004"]}})
    
    # implement this in inheriting classes if needs to be different
    def save_and_unqueue(self, item):
        # alter to use aliases method once exists
        item.save()
        log.debug("Saved and unqueued item " + item.id)
        
        
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
            my_item = Item(self.dao, id=row["id"])
            my_item.load() # TODO add better load methods to item so we don't have to go back to the db here
            items.append(my_item)

        '''
        # don't have time to do it the pythonic way...will learn later
        response_seeds = [i.items()[0][1] for i in items['rows']]
        response_items = [Item(self.dao, seed=seed) for seed in response_seeds]
        '''
        return items
    

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
            res = self.dao.view(viewname, startkey=[self.provider,0,0], endkey=[self.provider,9999999999,9999999999])
        else:
            res = self.dao.view(viewname)
        # due to error in couchdb this reads from json output - see dao view

        items = []
        for row in res["rows"]:
            my_item = Item(self.dao, id=row["id"])
            my_item.load() # TODO add better load methods to item so we don't have to go back to the db here
            items.append(my_item)
        return items

