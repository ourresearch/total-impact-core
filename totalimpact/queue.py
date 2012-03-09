from totalimpact.models import Item
import totalimpact.dao as dao
import datetime

# some data useful for testing
# d = {"DOI" : ["10.1371/journal.pcbi.1000361", "10.1016/j.meegid.2011.02.004"], "URL" : ["http://cottagelabs.com"]}

class Queue(dao.Dao):
    __type__ = None
        
    # TODO: 
    # return next item from this queue (e.g. whatever is on the top of the list
    # does NOT remove item from tip of queue
    def first(self):
        # turn this into an instantiation of an item based on the query result
        #if len(self.queue) > 0:
        #    return self.queue[0]
        #else:
        #    return None
        return Item(**{'_rev': '4-a3e3574c44c95b86bb2247fe49e171c8', '_id': 'test', '_deleted_conflicts': ['3-2b27cebd890ff56e616f3d7dadc69c74'], 'hello': 'world', 'aliases': {'URL': ['http://cottagelabs.com'], 'DOI': ['10.1371/journal.pcbi.1000361', "10.1016/j.meegid.2011.02.004"]}})
    
    # implement this in inheriting classes if needs to be different
    def save_and_unqueue(self,item):
        # alter to use aliases method once exists
        item.data[self.__type__]['last_updated'] = datetime.datetime.now()
        item.save()
        
        
class AliasQueue(Queue):
    __type__ = 'aliases'
    
    
class MetricsQueue(Queue):
    __type__ = 'metrics'
    
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
        addr = 'queues/' + self.__type__
        if self.provider:
            addr += '?key=["' + self.provider + '"]'
        items = self.view(addr)
        return [Item(**i['key']) for i in items.rows]

    def save_and_unqueue(self,item):
        # alter to use aliases method once exists
        if self.provider:
            item.data[self.__type__][self.provider]['last_updated'] = datetime.datetime.now()
            item.save()
        else:
            return 'No! you have not set a provider'
