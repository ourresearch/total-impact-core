# FIXME: this entire file is just for demonstration, and should be replaced with
# a proper set of objects.  Most of the operations here are SPURIOUS

import uuid

class Alias(object):
    def __init__(self, aliases=[]):
        self.aliases = aliases
        self.tiid = str(uuid.uuid4())
    
    def get_aliases(self):
        return self.aliases
        
class Metrics(object):
    
    def __init__(self):
        self.properties = {}
    
    def add(self, property, value):
        self.properties[property] = value
        
    def get(self, property, default_value):
        return self.properties.get(property, default_value)
        
    def add_metrics(self, other):
        # FIXME: use dstruct, or some other dictionary stitching algorithm
        # this just replaces everything in the current object with the other
        # object - nothing additive about it
        for p in other.properties.keys():
            self.properties[p] = other.properties[p]
            
    def __repr__(self):
        return str(self.properties)
        
    def __str__(self):
        return str(self.properties)