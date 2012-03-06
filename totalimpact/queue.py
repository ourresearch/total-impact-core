from totalimpact.model import Alias

class Queue(object):
    def next(self):
        # this should return an Alias object or None
        # it should NOT remove it from the tip of the queue
        
        # FIXME: just for testing
        alias_object = Alias([("doi", "10.1371/journal.pcbi.1000361"), ("url", "http://cottagelabs.com")])
        return alias_object
        
    def remove(self, alias_object):
        # remove the given alias_object from the tip of the queue
        pass