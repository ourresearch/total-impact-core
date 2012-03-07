from totalimpact.models import Aliases # remove this import once updated

from totalimpact import Item
import models from totalimpact
import totalimpact.dao as dao
import datetime

class Queue(dao.Dao):
    def next(self):
        # this should return an Alias object or None
        # it should NOT remove it from the tip of the queue
        
        # FIXME: just for testing
        d = {"doi" : ["10.1371/journal.pcbi.1000361"], "url" : ["http://cottagelabs.com"]}
        alias_object = Aliases(d)
        return alias_object
        
    def remove(self, alias_object):
        # remove the given alias_object from the tip of the queue
        pass
    
    
    # instantiate a queue:
    # tiid = total impact ID of item in question
    # qtype = aliases, metrics, errors, maybe more
    def __init__(self,qtype,provider=None):
        self.qtype = qtype
        self.provider = provider
        
    @property
    def queue(self):
        return self.query(self.qry)

    @property
    def qry(self):
        # define couchdb queries (or calls to couchdb queries)
        # that return the relevant information
        if self.qtype == 'aliases':
            _qry = {}
            
        if self.qtype == 'metrics':
            _qry = {}
            
        if self.qtype == 'errors':
            _qry = {}
        
        return _qry

    # the name of this will be changed to next when finished
    # return next item from this queue (e.g. whatever is on the top of the list
    # does NOT remove item from tip of queue
    def rnext(self):
        # turn this into an instantiation of an item based on the query result
        return Item(**self.queue[0])
    
    # the name of this will be changed to remove when finished
    def rremove(self, item):
        # change the last updated (or whatever it is actually called)
        # on either the aliases or the metrics
        if self.provider:
            item.data[self.qtype][self.provider]['last_updated'] = datetime.datetime.now()
        else:
            item.data[self.qtype]['last_updated'] = datetime.datetime.now()
        item.save()
        
