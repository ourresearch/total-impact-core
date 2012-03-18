from werkzeug import generate_password_hash, check_password_hash
import totalimpact.dao as dao
from totalimpact.config import Configuration
import time, uuid, json, hashlib
import time

# FIXME: do we want a created and last modified property on the user?
class User(dao.Dao):
    __type__ = 'user'
    
    """
    {
        "id": "1234f",
        "name": "jason priem",
        "email": "abcd@foo.com",
        "password": "1234fd56", # hash
        "collection_ids": ["abcd3", "abcd4"], # tiid
        "created": 12134234242.234,
        "last_modified": 1239898237.234
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
    

# FIXME: collection doesn't have an ID
# FIXME: may need to ditch the meta section
class Collection(dao.Dao):
    __type__ = 'collection'
    
    """
    {
        "collection_name": "My Collection",
        "owner": "abcdef",
        "created": 1328569452.406,
        "last_modified": 1328569492.406,
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
        if seed is not None: self.data = seed 
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:
            if id is not None: self.id = id
            self.data['ids'] = item_ids if item_ids is not None else []            
            self.data['collection_name'] = name if name is not None else None
            self.data['owner'] = owner if owner is not None else None
        
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
        

# FIXME: the code terminology and the docs terminology differ slightly:
# "alias" vs "aliases", "metric" vs "metrics"
# FIXME: do we want a created and last modified property on the item?
# FIXME: no id on the item? this should appear in the alias object?
class Item(dao.Dao):
    __type__ = 'item'
    
    """
    {
        "aliases": alias_object, 
        "metrics": metric_object, 
        "biblio": biblio_object,
        "created": 23112412414.234,
        "last_modified": 12414214.234,
        "last_requested": 124141245.234
    }
    """
    def __init__(self, id=None, aliases=None, metrics=None, biblio=None, seed=None, **kwargs):
        # for convenience with CouchDB we store all the properties in an internally
        # managed dict object which can just be json serialised out to the DAO
        
        # inherit the init
        super(Item,self).__init__(**kwargs)

        self.id = id
        if seed is not None: 
            self._data = seed
            self._aliases = Aliases(seed=self._data.get('aliases'))
            self._metrics = Metrics(seed=self._data.get('metrics'))
            self._biblio = Biblio(seed=self._data.get('biblio'))
        else:
            self._aliases = Aliases(seed=aliases) if hasattr(aliases, "keys") else aliases
            self._metrics = Metrics(seed=aliases) if hasattr(aliases, "keys") else metrics
            self._biblio = Biblio(seed=aliases) if hasattr(aliases, "keys") else biblio
                    
        # save the time of this request to the object
        self._data['last_requested'] = time.time()
        self.save()

    @property
    def aliases(self):
        try:
            return self._aliases
        except:
            self._aliases = Aliases(seed=self._data.get('aliases',None))
            return self._aliases

    @property
    def metrics(self):
        try:
            return self._metrics
        except:
            self._metrics = Metrics(seed=self._data.get('metrics',None))
            return self._metrics
        
    @property
    def biblio(self):
        try:
            return self._biblio
        except:
            self._biblio = Biblio(seed=self._data.get('biblio',None))
            return self._biblio
            
    @property
    def data(self):
        self._data['aliases'] = self.aliases.data
        self._data['metrics'] = self.metrics.data
        self._data['biblio'] = self.biblio.data
        return self._data

    @data.setter
    def data(self, val):
        self._data = val

# FIXME: there's no documentation on the biblio object, so just leaving
# it blank for the time being
class Biblio(object):
    def __init__(self, seed=None):
        self.data = seed if seed is not None else {}


class Metrics(object):
    """
    {
        "meta": {
            "PROVIDER_ID": {
                "last_modified": 128798498.234,
                "last_requested": 2139841098.234,
                "ignore": false
            }
        },
        "bucket":[
            "LIST OF PROVIDER METRIC OBJECTS"
        ]
    }
    """
    
    def __init__(self, seed=None):
        self.data = seed if seed is not None else {}
        
        if 'meta' not in self.data:
            self.data['meta'] = {}

        if 'bucket' not in self.data:
            self.data['bucket'] = {}
        
        # list all providers from config
        config = Configuration()
        for provider in config.providers:
            if provider['class'] not in self.data['meta'].keys():
                self.data['meta'][provider['class']] = {'last_modified':0, 'last_requested':time.time(), 'ignore':False}
        for item in self.data['meta']:
            self.data['meta'][item]['last_requested'] = time.time()

    def meta(self):
        return self.data['meta']
    
    def add_provider_metric(self, provider_metric):
        hash = self._hash(provider_metric)
        self.data['bucket'][hash] = provider_metric
        
    def list_provider_metrics(self):
        return self.data['bucket'].values()
        
    def _hash(self, provider_metric):
        # get a hash of the provider_metric's json representation
        j = json.dumps(provider_metric.data)
        m = hashlib.md5()
        m.update(j)
        return m.hexdigest()
        

# FIXME: should this have a created property?
# FIXME: should things like "can_use_commercially" be true/false rather than the - yes
# string "0" or "1", or are there other values that can go in there
class ProviderMetric(object):
    """
    {
        "id": "Mendeley:readers",
        "value": 16,
        "created": 1233442897.234,
        "last_modified": 1328569492.406,
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
    def __init__(self, id=None, value=None, last_modified=None, provenance_url=None, meta=None, seed=None):
                        
        # load from the seed first
        self.data = seed if seed is not None else {}
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:            
            self.data['id'] = self._init(id, str(uuid.uuid4()))
            self.data['value'] = self._init(value, 0)
            self.data['last_modified'] = self._init(last_modified, time.time())
            self.data['provenance_url'] = self._init(provenance_url, [])
            self.data['meta'] = self._init(meta, {})

        if "meta" not in self.data.keys():
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
                
    def __str__(self):
        return str(self.data)
    
    # FIXME: add a validation routine
    # FIXME: we need a nicer interface to get at the contents of the inner data object
    
class Aliases(object):
    """
    {
        "tiid":"123456",
        "title":["Why Most Published Research Findings Are False"],
        "url":["http:\/\/www.plosmedicine.org\/article\/info:doi\/10.1371\/journal.pmed.0020124"],
        "doi": ["10.1371\/journal.pmed.0020124"],
        "created": 12387239847.234,
        "last_modified": 1328569492.406
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
            if ids is None:
                return ret
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
        if self.data.get(namespace):
            return self.data.get(namespace)
        else:
            return []
    
    def add_alias(self, namespace, id):
        if namespace in self.data.keys():
            self.data[namespace].append(id)
        else:
            self.data[namespace] = [id]

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
    """
    def __setattr__(self, att, value):
        if att == "data":
            super(Aliases, self).__setattr__(att, value)
        else:
            self.data[att] = value
    """
    
    def __repr__(self):
        return "TIID: " + self.tiid + " " + str(self.data)
        
    def __str__(self):
        return "TIID: " + self.tiid + " " + str(self.data)

