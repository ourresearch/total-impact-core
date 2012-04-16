from werkzeug import generate_password_hash, check_password_hash
import totalimpact.dao as dao
from totalimpact.providers.provider import ProviderFactory
import time, uuid, json, hashlib, inspect, yaml, re

class Saveable(object):

    def __init__(self, dao, id=None):
        self.dao = dao

        if id is None:
            self.id = uuid.uuid4().hex
            self.created = time.time()
        else:
            self.id = id

    def as_dict(self, obj=None):
        '''Recursively calls __dict__ on itself and all constituent objects.

        Currently uses yaml as a ridiculous hack because recursive dict call
        turn out to be pretty difficult. None of the functions listed here
        http://stackoverflow.com/questions/1036409/recursively-convert-python-object-graph-to-dictionary
        work.
        '''

        str = yaml.dump(self)
        str = re.sub(r'!![^\s]+ *', '', str)
        return  yaml.load(str)


    def _update_dict(self, input, my_dict=None):
        '''Use another dict to recursively add list or dict items not in this.
        
        This object's value wins all conflicts, but new values in lists and 
        dictionaries are added. Used to update from the db before saving.
        I think this might should go in the dao...not sure.

        returns - dict
        '''
        if my_dict is None:
            my_dict = self.as_dict()

        for k, v in input.iteritems():
            try:
                new_my_dict = my_dict.setdefault(k, {})
                self._update_dict(v, new_my_dict)
            except AttributeError:
                if not my_dict[k]:
                    my_dict[k] = v
        
        return my_dict

    def save(self):
        new_dict = self.dao.get(self.id)
        dict_to_save = self._update_dict(new_dict)
        res = self.dao.save(dict_to_save)
        return res

    def delete(self):
        self.dao.delete(self.id)
        return True



class ItemFactory():

    @staticmethod
    def make(dao, tiid=None):
        item = Item(dao=dao, id=tiid)

        if tiid is not None: # we're making a brand new item
            item_doc = dao.get(tiid)

            if item_doc is None:
                raise LookupError

            for k in item_doc:
                setattr(item, k, item_doc[k])

            # some of the item's properties are objects, not dictionaries.
            # we make these objects using doc data, then put them in the item.
            item.aliases = Aliases(seed=item_doc['aliases'])
            item.metrics = {}

            for metric_name, metrics_dict in item_doc['metrics'].iteritems():
                my_metric_obj = Metrics()
                for k, v in metrics_dict.iteritems():
                    setattr(my_metric_obj, k, v)
    
                item.metrics[metric_name] = my_metric_obj

            item.last_requested = time.time()
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



    def save(self, dao):
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

class CollectionFactory():
    def __init__(self, dao):
        self.dao = dao

    def make(self, id=None):
        collection = Collection(dao=self.dao)

        if id is None:
            collection.id = uuid.uuid4().hex
        else: # load an extant item
            collection_doc = self.dao.get(id)
            if collection_doc is None:
                raise LookupError
            
            for k in collection_doc:
                setattr(collection, k, item_doc[k])

        return collection


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
    def __init__(self):

        self.ignore = False
        self.metric_snaps = {}
        self.latest_snap = None
        # no need to set a last_modified...it's just the last_modified of self.latest
        
    def add_metric_snap(self, metric_snap):
        '''Stores a MetricSnap object based on a key hashed from its "value" attr.

        When you get the snap back out, you're getting the object, not its attributes.
        Also, note that snaps with identical values get overwritten.
        '''

        hash = hashlib.md5(str(metric_snap["value"])).hexdigest()
        self.metric_snaps[hash] = metric_snap
        self.latest_snap = metric_snap
        self.last_modified = time.time()
        return hash


      


# FIXME: should this have a created property?
# FIXME: should things like "can_use_commercially" be true/false rather than the - yes
# string "0" or "1", or are there other values that can go in there
# FIXME: add a validation routine
# FIXME: we need a nicer interface to get at the contents of the inner data object
# just here for documentation purposes right now...
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
    
    def __init__(self, seed=None):
        self.created = time.time() # will get overwritten if need be
        try:
            for k in seed:
                setattr(self, k, seed[k])
        except TypeError:
            pass

    def add_alias(self, namespace, id):
        try:
            attr = getattr(self, namespace)
            attr.append(id)
            print attr
        except AttributeError:
            setattr(self, namespace, [id])
        self.last_modified = time.time()

    #FIXME: this should take namespace and id, not a list of them
    def add_unique(self, alias_list):
        for ns, id in alias_list:
            try:
                if id not in getattr(self, ns):
                    self.add_alias(ns, id)
            except:
                    self.add_alias(ns, id)
        self.last_modified = time.time()
    
    def get_aliases_list(self, namespace_list=None): 
        ''' 
        gets list of this object's aliases in each given namespace
        
        returns a list of (namespace, id) tuples
        '''
        # if this is a get on everything, just summon up the items
        if namespace_list is None:
            return [x for x in self.__dict__ if x not in self.not_aliases]
        
        # if the caller doesn't pass us a list, but just a single value, wrap it
        # up for them
        if not hasattr(namespace_list, "append"):
            namespace_list = [namespace_list]
        
        # otherwise, get for the specific namespaces
        ret = []
        for namespace in namespace_list:
            ids = getattr(self, namespace)
            
            # crazy hack TODO fix lists/strings flying about
            if not hasattr(ids, "append"):
                ids = [ids]
            ret += [(namespace, id) for id in ids]

        return ret

    # FIXME I don't think we need this any more?
    def as_dict(self):
        return self.__dict__


