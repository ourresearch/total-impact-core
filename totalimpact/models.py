from werkzeug import generate_password_hash, check_password_hash
import totalimpact.dao as dao
from totalimpact.providers.provider import ProviderFactory
import time, uuid, json, hashlib, inspect

class Saveable(object):

    def __init__(self, id=None):
        self.id = id #set it properly below

        if id is None:
            self.id = uuid.uuid4().hex
        else:
            self.id = id

    def as_dict(self):
        '''Recursively calls __dict__ on itself and all constituent objects.'''

        data = {}
        for key, value in self.__dict__.iteritems():
            if key == "dao": continue
            try:
                data[key] = self.as_dict(value)
            except AttributeError:
                data[key] = value
        return data

    def __str__(self):
        return str(self.as_dict())


class ItemFactory():

    def __init__(self, dao):
        self.dao = dao

    def make(self, tiid=None):
        now = time.time()
        item = Item()
        item.last_modified = now

        if tiid is None: # we're making a brand new item
            item.created = now
        else: # load an extant item
            item_doc = self.dao.get(tiid)
            for k in item_doc:
                setattr(item, k, item_doc[k])

            # some of the item's properties are objects, not dictionaries.
            # we make these objects using doc data, then put them in the item.
            item.aliases = Aliases(seed=item_doc['aliases'])
            item.metrics = []
            '''
            for i in item_doc['metrics']:
                my_metric_dict = item_doc['metrics'][i]


                my_metric_obj = Metrics(my_metric_dict["metric_name"])



                my_metric_obj["ignore"] = my_metric_dict["ignore"]

                latest_snap = MetricSnap(seed=my_metric_dict["latest_snap"])
                my_metric_obj["latest_snap"] = latest_snap
                for s in my_metric_dict["metric_snaps"]:
                    snap = MetricSnap(seed=my_metric_dict["metric_snaps"][s])
                    my_metric_obj.metric_snaps[s] = snap

                item.metrics.append(my_metric_obj)
                '''


        return item



# FIXME: no id on the item? this should appear in the alias object?
class Item(Saveable):
    """{
        "id": "uuid4-goes-here",
        "aliases": "aliases_object",
        "metrics": "metric_object",
        "biblio": "biblio_object",
        "created": 23112412414.234,
        "last_modified": 12414214.234,
        "last_requested": 124141245.234
    }
    """

    pass


class Error(Saveable):
    """{
        "error_type": "http_timeout",
        "message": "Error opening file",
        "provider": "github_provider",
        "id": "uuid4-goes-here",
        "stack_trace": "Python Stacktrace"
    }"""
    pass

        
class Collection(Saveable):
    """
    {
        "id": "uuid-goes-here",
        "collection_name": "My Collection",
        "owner": "abcdef",
        "created": 1328569452.406,
        "last_modified": 1328569492.406,
        "item_tiids": ["abcd3", "abcd4"]
    }
    """
        
    def item_ids(self):
        if not hasattr(self, "item_tiids"): 
            self.item_tiids = []
        return self.item_tiids
        
    def add_item(self, new_item_id):
        if not hasattr(self, "item_tiids"): 
            self.item_tiids = []
        if new_item_id not in self.item_tiids:
            self.item_tiids.append(new_item_id)
    
    def add_items(self, new_item_ids):
        if not hasattr(self, "item_tiids"): 
            self.item_tiids = []
        for item_id in new_item_ids:
            self.add_item(item_id)
    
    def remove_item(self, item_id):
        if not hasattr(self, "item_tiids"): 
            self.item_tiids = []
        if item_id in self.item_tiids:
            self.item_tiids.remove(item_id)



class Biblio(object):
    """
    {
        "title": "An extension of de Finetti's theorem", 
        "journal": "Advances in Applied Probability", 
        "author": [
            "Pitman, J"
        ], 
        "collection": "pitnoid", 
        "volume": "10", 
        "id": "p78", 
        "year": "1978", 
        "pages": "268 to 270"
    }
    """
    def __init__(self, seed=None):
        self.data = seed if seed is not None else ""
            
    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self.data)


class Metrics(object):
    '''
    This is set up to only deal with *one* type of metric; plos:pdf_view and
    plos:html_views, for example, need different Metrics objects despite being
    from the same provider.
    '''
    def __init__(self, provider_name, metric_name):

        self.metric_name = metric_name
        self.provider_name = provider_name
        self.ignore = False
        self.metric_snaps = {}
        self.latest_snap = None
        
    def add_metric_snap(self, metric_snap):
        '''Stores a MetricSnap object based on a key hashed from its "value" attr.

        When you get the snap back out, you're getting the object, not its attributes.
        Also, note that snaps with identical values get overwritten.
        '''

        hash = hashlib.md5(str(metric_snap.data["value"])).hexdigest()
        self.metric_snaps[hash] = metric_snap
        self.latest_snap = metric_snap
        self.last_modified = time.time()
        return hash
        
    
      


# FIXME: should this have a created property?
# FIXME: should things like "can_use_commercially" be true/false rather than the - yes
# string "0" or "1", or are there other values that can go in there
# FIXME: add a validation routine
# FIXME: we need a nicer interface to get at the contents of the inner data object
class MetricSnap(object):
    """
    {
        "id": "Mendeley:readers",
        "value": 16,
        "created": 1233442897.234,
        "last_modified": 1328569492.406,
        "provenance_url": ["http:\/\/api.mendeley.com\/research\/public-chemical-compound-databases\/"],
        "static_meta": {
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
    def __init__(self, id=None, value=None, created=None, last_modified=None, provenance_url=None, static_meta=None, seed=None):
                        
        # load from the seed first
        self.data = seed if seed is not None else {}
        
        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:            
            self.data['id'] = self._init(id, str(uuid.uuid4()))
            self.data['value'] = self._init(value, 0)
            self.data['created'] = self._init(created, time.time())
            self.data['last_modified'] = self._init(last_modified, time.time())
            self.data['static_meta'] = self._init(static_meta, {})
            
            # provenance url needs a bit of special treatment
            if not hasattr(provenance_url, "append"):
                self.data['provenance_url'] = [provenance_url]
            else:
                self.data['provenance_url'] = []

        if "static_meta" not in self.data.keys():
            self.data['static_meta'] = {}
        
    def value(self, val=None):
        if val is None:
            return self.data['value']
        else:
            self.data['value'] = val
            self.data['last_modified'] = time.time()
            
    def static_meta(self, static_meta=None):
        if static_meta is None:
            return self.data['static_meta']
        else:
            self.data['static_meta'] = static_meta
            self.data['last_modified'] = time.time()
    
    def __repr__(self):
        return str(self.data)


    # FIXME: this is not particularly intuitive, consider changing it
    def provenance(self, provenance=None):
        """
        get or set the provenance.
        
        This will retrieve the provenance array if urls is None
        If urls is not a list, the url will be appended to the existing urls
        If urls IS a list, it will overwrite the existing provenance list
        """
        if provenance is None:
            return self.data['provenance_url']
        else:
            if hasattr(provenance, "append"):
                self.data['provenance_url'] = provenance
            else:
                self.data['provenance_url'].append(provenance)
            self.data['last_modified'] = time.time()
    
    def _init(self, val, default=None):
        return val if val is not None else default
    
    def __getattribute__(self, att):
        try:
            return super(MetricSnap, self).__getattribute__(att)
        except:
            return self.data[att]
    
    def __str__(self):
        return str(self.data)

    '''
    def __eq__(self, other):
        return self.data == other.data
    '''
    

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
    
    not_aliases = ["created", "last_modified"]
    
    def __init__(self, tiid=None, seed=None, **kwargs):
        # load from the seed first
        self.data = seed if seed is not None else {}
        
        if self.data.has_key("tiid"):
            tiid = self.data["tiid"]
        if not tiid:
            tiid = str(uuid.uuid4())

        # if there was no seed, load the properties, otherwise ignore them
        if seed is None:
            self.data["tiid"] = tiid
            for arg, val in kwargs.iteritems():
                if hasattr(val, "append"):
                    self.data[arg] = val
                else:
                    self.data[arg] = [val]
        else:
            if not self.data.has_key("tiid"):
                self.data["tiid"] = tiid

    def add_alias(self, namespace, id):
        if namespace in self.data.keys():
            if not hasattr(self.data[namespace], "append"):
                self.data[namespace] = [self.data[namespace]]
            self.data[namespace].append(id)
        else:
            self.data[namespace] = [id]


    def add_unique(self, alias_list):
        for ns, id in alias_list:
            if id not in self.data.get(ns, []):
                self.add_alias(ns, id)
    
    def get_ids_by_namespace(self, namespace):
        ''' gets list of this object's ids in each given namespace
        
        returns [] if no ids
        >>> a = Aliases()
        >>> a.add_alias("foo", "id1")
        >>> a.get_ids_by_namespace("foo")
        ['id1']
        '''
        return self.data.get(namespace, [])
    
    def get_aliases_list(self, namespace_list=None): 
        ''' 
        gets list of this object's aliases in each given namespace
        
        returns a list of (namespace, id) tuples
        '''
        # if this is a get on everything, just summon up the
        # items
        if namespace_list is None:
            return [x for x in self.data.items() if x[0] not in self.not_aliases]
        
        # if the caller doesn't pass us a list, but just a single value, wrap it
        # up for them
        if not hasattr(namespace_list, "append"):
            namespace_list = [namespace_list]
        
        # otherwise, get for the specific namespaces
        ret = []
        for namespace in namespace_list:
            ids = self.get_ids_by_namespace(namespace)
            
            # crazy hack TODO fix lists/strings flying about
            if not hasattr(ids, "append"):
                ids = [ids]
            ret += [(namespace, id) for id in ids]
        
        return ret
    
    def get_aliases_dict(self):
        return self.data

    def as_dict(self):
        # renamed for consistancy with Items(); TODO cleanup old one
        return self.data

    def __getattribute__(self, att):
        try:
            return super(Aliases, self).__getattribute__(att)
        except AttributeError:
            return self.data[att]
                
    def __repr__(self):
        return "TIID: " + self.tiid + " " + str(self.data)
        
    def __str__(self):
        return "TIID: " + self.tiid + " " + str(self.data)

