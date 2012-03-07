import uuid, os, json
import totalimpact.dao as dao
from collections import defaultdict

from werkzeug import generate_password_hash, check_password_hash
from flaskext.login import UserMixin

class emptyMetricsError(Exception):
    pass

class Aliases:
    ''' handles all the identifiers for an Item.'''
    
    def __init__(self, seed=None):
        if seed is None:
            self.tiid = str(uuid.uuid1())
            self.data = defaultdict(list)
        else:
            self._validate_seed(seed)
            self.tiid = seed.get("tiid", str(uuid.uuid1()))
            self.data = defaultdict(list, seed)
    
    def _validate_seed(self, seed):
        # FIXME: what does this actually do?
        pass
    
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
        self.data[namespace].append(id) # using defaultdict, no need to test if list exists first
        
    def add_unique(self, alias_list):
        for ns, id in alias_list:
            if id not in self.data[ns]:
                self.add_alias(ns, id)
    
    def __repr__(self):
        return "TIID: " + self.tiid + " " + str(self.data)
        
    def __str__(self):
        return "TIID: " + self.tiid + " " + str(self.data)

class Metrics:

    def __init__(self, seed=None):
        self.properties = {} if seed is None else seed
        #here = os.path.dirname(os.path.realpath(__file__))
        #fp = open(here + '/../test/complete_metric.json')
        #self.example_seed = json.load(fp)
    
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

    def is_complete(self):
        if 0:
            return True
        else:
            return False
 
class Item(dao.Dao):
    __type__ = 'item'
        
class Collection(dao.Dao):
    __type__ = 'collection'
    
class User(dao.Dao,UserMixin):
    __type__ = 'user'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)


