from werkzeug import generate_password_hash, check_password_hash
import totalimpact.dao as dao
import time, uuid

# FIXME: do we want a created and last modified property on the user?
class User(dao.Dao):
    __type__ = 'user'
    
    """
    {
        "id": "1234f",
        "name": "jason priem",
        "email": "abcd@foo.com",
        "password": "1234fd56", # hash
        "collection_ids": ["abcd3", "abcd4"] # tiid
    }
    """
    def __init__(self, id=None, password=None, password_hash=None, name=None, 
                        email=None, collections=None, seed=None):
        # for convenience with CouchDB we store all the properties in an internally
        # managed dict object which can just be json serialised out to the DAO
        # This object has a __getattr__ override below which makes the object 
        # appear as if all the dictionary keys are member attributes of this object
        
        # inherit the init
        super(User,self).__init__()
        
        # load from the seed first
        self.data = seed if seed is not None else {}
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:
            self.data['id'] = id if id is not None else str(uuid.uuid4())
            
            if password is not None:
                self.set_password(password)
            elif password_hash is not None:
                self.data['password'] = password_hash
            
            self.data['collections'] = collections if collections is not None else []
            self.data['name'] = name if name is not None else None
            self.data['email'] = email if email is not None else None
    
    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)
        
    def collection_ids(self):
        return self.data['collections']
        
    def add_collection(self, collection_id):
        if collection_id not in self.data['collections']:
            self.data['collections'].append(collection_id)
    
    def remove_collection(self, collection_id):
        if collection_id in self.data['collections']:
            self.data['collections'].remove(collection_id)
    
    # FIXME: we need a nicer API to get at the contents of the inner
    # data object
    def __getattribute__(self, att):
        try:
            return super(User, self).__getattribute__(att)
        except:
            return self.data[att]
    def __setattr__(self, att, value):
        if att == "data":
            super(User, self).__setattr__(att, value)
        else:
            self.data[att] = value

# FIXME: collection doesn't have an ID
# FIXME: may need to ditch the meta section
class Collection(dao.Dao):
    __type__ = 'collection'
    
    """
    {
        "meta": {
            "collection_name": "My Collection",
            "owner": "abcdef",
            "created": 1328569452.406,
            "last_modified": 1328569492.406,
        }
        "ids": ["abcd3", "abcd4"]  #tiid
    }
    """
    def __init__(self, id=None, name=None, owner=None, created=None, last_modified=None, 
                        item_ids=None, seed=None):
        # for convenience with CouchDB we store all the properties in an internally
        # managed dict object which can just be json serialised out to the DAO
        # This object has a __getattr__ override below which makes the object 
        # appear as if all the dictionary keys are member attributes of this object

        # inherit the init
        super(Collection,self).__init__()
        
        # load from the seed first
        self.data = seed if seed is not None else {}
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:
            self.data['meta'] = {}
            
            self.data['id'] = id if id is not None else str(uuid.uuid4())
            self.data['ids'] = item_ids if item_ids is not None else []
            
            self.data['meta']['collection_name'] = name if name is not None else None
            self.data['meta']['owner'] = owner if owner is not None else None
            self.data['meta']['created'] = created if created is not None else time.time()
            self.data['meta']['last_modified'] = last_modified if last_modified is not None else time.time()
        else:
            # we need to ensure that meta is initialised
            self.data['meta'] = {}
        
    def item_ids(self):
        return self.data['ids']
        
    def add_item(self, item_id):
        if item_id not in self.data['ids']:
            self.data['ids'].append(item_id)
    
    def add_items(self, item_ids):
        for item in item_ids:
            self.add_item(item)
    
    def remove_item(self, item_id):
        if item_id in self.data['ids']:
            self.data['ids'].remove(item_id)
        
    # FIXME: we need a nicer API to get at the contents of the inner
    # data object
    def __getattribute__(self, att):
        try:
            return super(Collection, self).__getattribute__(att)
        except:
            return self.data[att]
    def __setattr__(self, att, value):
        if att == "data":
            super(Collection, self).__setattr__(att, value)
        else:
            self.data[att] = value

# FIXME: the code terminology and the docs terminology differ slightly:
# "alias" vs "aliases", "metric" vs "metrics"
# FIXME: do we want a created and last modified property on the item?
# FIXME: no id on the item? this should appear in the alias object?
class Item(dao.Dao):
    __type__ = 'item'
    
    """
    {
        "alias": alias_object, 
        "metric": metric_object, 
        "biblio": biblio_object
    }
    """
    def __init__(self, id=None, aliases=None, metrics=None, biblio=None, seed=None, **kwargs):
        # for convenience with CouchDB we store all the properties in an internally
        # managed dict object which can just be json serialised out to the DAO
        # This object has a __getattr__ override below which makes the object 
        # appear as if all the dictionary keys are member attributes of this object
        
        # FIXME: implement seed support (this is a bit tricky, as aliases,
        # metrics and biblio are objects)
        
        # inherit the init
        super(Item,self).__init__(**kwargs)

        if id:
            self.data['_id'] = id

        self.aliases = aliases if aliases is not None else Aliases(seed=self.data.get('aliases',None))
        self.metrics = metrics if metrics is not None else Metrics(seed=self.data.get('metrics',None))
        self.biblio = biblio if biblio is not None else Biblio(seed=self.data.get('biblio',None))

        if seed:
            self.data = seed
        
    @property
    def data(self):
        self.data['aliases'] = self.aliases.data
        self.data['metrics'] = self.metrics.data
        self.data['biblio'] = self.biblio.data
        return self.data

    @data.setter
    def data(self, val):
        self = val
            
    # FIXME: we need a nicer API to get at the contents of the inner
    # data object
    #def __getattr__(self, att):
    #    try:
    #        super(Item, self).__getattr__(att)
    #    except:
    #        self.data.get(att, None)

# FIXME: there's no documentation on the biblio object, so just leaving
# it blank for the time being
class Biblio(object):
    def __init__(self, seed=None):
        pass

class Metrics(object):
    
    def __init__(self, seed=None):
        self.data = seed if seed is not None else {}
    
    def add_provider_metric(self, provider_metric):
        # FIXME: implement
        pass
        
    def list_provider_metrics(self):
        # FIXME: implement
        pass
        
    def _hash(self, provider_metric):
        # get a hash of the provider_metric's json representation
        pass

# FIXME: should this have a created property?
# FIXME: should things like "can_use_commercially" be true/false rather than the - yes
# string "0" or "1", or are there other values that can go in there
class ProviderMetric(object):
    """
    {
        "id": "Mendeley:readers",
        "value": 16,
        "last_update": 1328569492.406,
        "provenance_url": "http:\/\/api.mendeley.com\/research\/public-chemical-compound-databases\/",
        "meta": {
            "display_name": "readers"
            "provider": "Mendeley",
            "provider_url": "http:\/\/www.mendeley.com\/",
            "description": "Mendeley readers: the number of readers of the article",
            "icon": "http:\/\/www.mendeley.com\/favicon.ico",
            "category": "bookmark",
            "can_use_commercially": "0",
            "can_embed": "1",
            "can_aggregate": "1",
            "other_terms_of_use": "Must show logo and say 'Powered by Santa'",
        }
    }
    """
    def __init__(self, id=None, value=None, last_update=None, provenance_url=None,
                        display_name=None, provider=None, provider_url=None,
                        description=None, icon=None, category=None, can_use_commercially=None,
                        can_embed=None, can_aggregate=None, other_terms_of_use=None,
                        seed=None):
                        
        # load from the seed first
        self.data = seed if seed is not None else {}
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:
            self.data['meta'] = {}
            
            self.data['id'] = self._init(id, str(uuid.uuid4()))
            self.data['value'] = self._init(value, 0)
            self.data['last_update'] = self._init(last_update, time.time())
            self.data['provenance_url'] = self._init(provenance_url, [])
            self.data['meta']['display_name'] = self._init(display_name)
            self.data['meta']['provider'] = self._init(provider)
            self.data['meta']['provider_url'] = self._init(provider_url)
            self.data['meta']['description'] = self._init(description)
            self.data['meta']['icon'] = self._init(icon)
            self.data['meta']['category'] = self._init(category)
            self.data['meta']['can_use_commercially'] = self._init(can_use_commercially, "0")
            self.data['meta']['can_embed'] = self._init(can_embed, "0")
            self.data['meta']['can_aggregate'] = self._init(can_aggregate, "0")
            self.data['meta']['other_terms_of_use'] = self._init(other_terms_of_use)
            
        else:
            # we need to ensure that meta is initialised
            self.data['meta'] = {}
    
    def _init(self, val, default=None):
        return val if val is not None else default
        
    def value(self, val=None):
        if val is None:
            return self.data['value']
        else:
            self.data['value'] = val
            
    def meta(self, meta=None):
        if meta is None:
            return self.data['meta']
        else:
            self.data['meta'] = meta
    
    def provenance(self, url=None):
        if url is None:
            return self.data['provenance_url']
        else:
            self.data['provenance_url'].append(url)
    
    def sum(self, other):
        # sum should take all the data out of other that is relevant to
        # the self, and sum them appropriate.  In practice this is just
        # the value and the provenance_url
        self.data['value'] += other.data['value']
        self.data['provenance_url'] += other.data['provenance']
    
    # FIXME: this is a validation routine, and need to validate the
    # object
    def is_complete(self):
        if 0:
            return True
        else:
            return False
    
    # FIXME: we need a nicer API to get at the contents of the inner
    # data object
    def __getattribute__(self, att):
        try:
            return super(ProviderMetric, self).__getattribute__(att)
        except:
            return self.data[att]
    def __setattr__(self, att, value):
        if att == "data":
            super(ProviderMetric, self).__setattr__(att, value)
        else:
            self.data[att] = value
    
class Aliases(object):
    """
    {
        "tiid":"123456",
        "title":["Why Most Published Research Findings Are False"],
        "url":["http:\/\/www.plosmedicine.org\/article\/info:doi\/10.1371\/journal.pmed.0020124"],
        "doi": ["10.1371\/journal.pmed.0020124"]
        ...
    }
    """
    def __init__(self, tiid=None, seed=None, **kwargs):
        # load from the seed first
        self._validate_seed(seed)
        self.data = seed if seed is not None else {}
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:
            self.data['tiid'] = self._init(tiid, str(uuid.uuid4()))
            for arg, val in kwargs.iteritems():
                if hasattr(val, "append"):
                    self.data[arg] = val
                else:
                    self.data[arg] = [val]
        else:
            if not self.data.has_key("tiid"):
                self.data['tiid'] = self._init(tiid, str(uuid.uuid4()))
    
    def get_aliases_list(self, namespace_list): 
        ''' 
        gets list of this object's aliases in each given namespace
        
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
    
    def _init(self, val, default=None):
        return val if val is not None else default
    
    def _validate_seed(self, seed):
        # FIXME: what does this actually do?
        pass
    
    def __getattribute__(self, att):
        try:
            return super(Aliases, self).__getattribute__(att)
        except:
            return self.data[att]
    def __setattr__(self, att, value):
        if att == "data":
            super(Aliases, self).__setattr__(att, value)
        else:
            self.data[att] = value
    
    def __repr__(self):
        return "TIID: " + self.tiid + " " + str(self.data)
        
    def __str__(self):
        return "TIID: " + self.tiid + " " + str(self.data)

"""
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
    
    @property
    def aliases(self):
        try:
            return self._als
        except:
            self._als = Aliases(seed=self.data.get('aliases',{}))
            return self._als

    @property
    def metrics(self):
        try:
            return self._ms
        except:
            self._ms = Metrics(seed=self.data.get('metrics',{}))
            return self._ms
        
    @property
    def data(self):
        try:
            self._data['aliases'] = self._als.get_aliases_dict
        except:
            pass
        try:
            self._data['metrics'] = dict(self._ms)
        except:
            pass
        return self._data
    
    # FIXME: Mark - can you check this is The Way with a Couch object?
    def set_metrics(self, metrics):
        self._ms = metrics
        
    def set_aliases(self, aliases):
        self._als = aliases
        
class Collection(dao.Dao):
    __type__ = 'collection'
    
class User(dao.Dao,UserMixin):
    __type__ = 'user'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

"""
