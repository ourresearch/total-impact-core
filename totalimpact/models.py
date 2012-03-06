import uuid
from collections import defaultdict

from werkzeug import generate_password_hash, check_password_hash
from flaskext.login import UserMixin

class Aliases:
    ''' handles all the identifiers for an Item.'''
    
    def __init__(self):
        self.tiid = str(uuid.uuid1())
        self.data = defaultdict(list)
    
    def get_aliases_list(self, namespace_list): 
        ''' gets list of this object's aliases in each given namespace
        
        returns a list of (namespace, id) tuples
        '''
        
        ret = []
        for namespace in namespace_list:
            ids = self.get_ids_by_namespace(namespace)
            for id in ids:
                ret.append((namespace, id))
        
        return ret
    
    def get_aliases_dict(self):
        return self.data
        
    def get_ids_by_namespace(self, namespace):
        ''' gets list of this object's ids in each given namespace
        
        returns [] if no ids
        >>> a = Aliases()
        >>> a.add_alias("foo", "id1")
        >>> a.get_ids_by_namespace("foo")
        ['id1']
        '''
        return self.data[namespace]    
    
    def add_alias(self, namespace, id):
        self.data[namespace].append(id)

class metrics:
    pass

    
class Item(object):
    def __init__(self):
        pass
    
class Collection(object):
    def __init__(self):
        pass
    
class User(UserMixin):
    def __init__(self):
        pass
    
    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)


