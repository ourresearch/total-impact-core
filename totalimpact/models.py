import uuid
from collections import defaultdict

class aliases:
    ''' handles all the identifiers for an Item.'''
    
    def __init__(self):
        self.tiid = str(uuid.uuid1())
        self.data = defaultdict(list)
    
    def get_ids(self, namespace): 
        ''' gets list of this object's ids in a given namespace
        
        returns [] if no ids
        '''
        return self.data[namespace]
    
    def add_alias(self, namespace, id):
        self.data[namespace].append(id)
        
    
    
        

class metrics:
    pass
