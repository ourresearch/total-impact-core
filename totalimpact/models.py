import uuid
from collections import defaultdict

class aliases:
    ''' handles all the identifiers for an Item.'''
    
    def __init__(self):
        self.tiid = str(uuid.uuid1())
        self.data = defaultdict(list)
    
    def get_aliases(self, namespace_list): 
        ''' gets list of this object's aliases in each given namespace
        
        returns a list of (namespace, id) tuples
        '''
        
        ret = []
        for namespace in namespace_list:
            ids = self.get_ids_by_namespace(namespace)
            for id in ids:
                ret.append((namespace, id))
        
        return ret
    
    def get_ids_by_namespace(self, namespace):
        ''' gets list of this object's ids in each given namespace
        
        returns [] if no ids
        '''
        return self.data[namespace]    
    
    def add_alias(self, namespace, id):
        self.data[namespace].append(id)
        
    
    
        

class metrics:
    pass
