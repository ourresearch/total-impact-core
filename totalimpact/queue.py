from totalimpact.models import Aliases

class Queue(object):
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