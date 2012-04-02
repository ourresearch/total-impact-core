import time

from totalimpact.models import Item

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)

# some data useful for testing
# d = {"DOI" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "URL" : ["http://cottagelabs.com"]}


class Queue():
    __type__ = None
        
    # TODO: 
    # return next item from this queue (e.g. whatever is on the top of the list
    # does NOT remove item from tip of queue
    def first(self):
        if len(self.queue) > 0:
            return self.queue[0]
        else:
            return None
        #return Item(**{'_rev': '4-a3e3574c44c95b86bb2247fe49e171c8', '_id': 'test', '_deleted_conflicts': ['3-2b27cebd890ff56e616f3d7dadc69c74'], 'hello': 'world', 'aliases': {'URL': ['http://cottagelabs.com'], 'DOI': ['10.1371/journal.pcbi.1000361', "10.1016/j.meegid.2011.02.004"]}})
    
    # implement this in inheriting classes if needs to be different
    def save_and_unqueue(self, item):
        # alter to use aliases method once exists
        item.save()
        log.debug("Saved and unqueued item " + item.id)
        
        
class AliasQueue(Queue):
    __type__ = 'aliases'
    
    def __init__(self, dao):
        self.dao = dao

    @property
    def queue(self):
        viewname = 'queues/' + self.__type__
        items = self.dao.view(viewname)
        # due to error in couchdb this reads from json output - see dao view

        #response = [Item(**i['value']) for i in items['rows']]
        response_seeds = [i.items()[0][1] for i in items['rows']]
        response_items = [Item(self.dao, seed=seed) for seed in response_seeds]
        log.info(i.keys()[0])
        log.info(response_items[0])
        return response_items
    

class MetricsQueue(Queue):
    __type__ = 'metrics'
    
    def __init__(self, dao, prov=None):
        # inherit the init
        ### FIXME is breaking super(MetricsQueue, self).__init__()
        self.dao = dao
        self._provider = prov
    
    @property
    def provider(self):
        try:
            return self._provider
        except:
            self._provider = None
            return self._provider
        
    @provider.setter
    def provider(self, _provider):
        self._provider = _provider

    @property
    def queue(self):
        # change this for live
        viewname = 'queues/' + self.__type__
        if self.provider:
            items = self.dao.view(viewname, startkey=[self.provider,0,0], endkey=[self.provider,9999999999,9999999999])
        else:
            items = self.dao.view(viewname)
        # due to error in couchdb this reads from json output - see dao view

        response = [Item(**i['value']) for i in items['rows']]
        return response

