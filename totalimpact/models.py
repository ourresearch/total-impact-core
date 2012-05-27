from werkzeug import generate_password_hash, check_password_hash
import totalimpact.dao as dao
from totalimpact import default_settings
from totalimpact.providers.provider import ProviderFactory
import time, uuid, json, hashlib, inspect, re, copy, string, random, datetime

import threading
from pprint import pprint

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('models')

def todict(obj, classkey=None, ignore=None):
    """ Convert an object to a diff representation 
        Recipe from http://stackoverflow.com/questions/1036409/recursively-convert-python-object-graph-to-dictionary
        Added in an extra parameter 'ignore' as 
        copying the dao is horribly horribly slow
    """
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = todict(obj[k], classkey, ignore)
        return obj
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey, ignore)) 
            for key, value in obj.__dict__.iteritems() 
            if not callable(value) and not key.startswith('_')
            and not key in ignore])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj

class GlobalItemLock:

    def __init__(self):
        self.lock = threading.Lock()
        self.itemLock = {}

    def getItemLock(self, item_id):
        self.lock.acquire()
        if not self.itemLock.has_key(item_id):
            self.itemLock[item_id] = threading.Lock()
        self.lock.release()
        return self.itemLock[item_id]
 

itemlock = GlobalItemLock()


class Saveable(object):

    def __init__(self, dao, id=None):
        self.dao = dao

        if id is None:
            self.id = uuid.uuid1().hex
        else:
            self.id = id

    def as_dict(self, obj=None, classkey=None):
        ''' Recursively convert this object's members into a dictionary structure for 
            serialisation to the database.
        '''
        start_time = datetime.datetime.now().isoformat()
        dict_repr = todict(self, ignore=['dao'])
        return dict_repr


    def save(self):
        return self.save_simple()

    def save_simple(self):
        retry = True
        import couchdb

        logger.info("IN SIMPLE SAVE with item %s" %self.id)

        while retry:
            try:
                res = self.dao.save_and_commit(self.as_dict())
                retry = False
            except couchdb.ResourceConflict, e:
                logger.info("Couch conflict, will retry")

        return res        

    def delete(self):
        self.dao.delete(self.id)
        return True


class Item(Saveable):
    pass


class ItemFactory():
    #TODO this should subclass a SaveableFactory

    item_class = Item
    all_static_meta = ProviderFactory.get_all_static_meta()

    @classmethod
    def build_item(cls, item_doc, snaps):
        item = {}
        item["id"] = item_doc["_id"]
        item["aliases"] = item_doc["aliases"]
        item["biblio"] = item_doc["biblio"]
        item["biblio"]['genre'] = cls.decide_genre(item_doc['aliases'])
        item["created"] = item_doc["created"]
        item["last_modified"] = item_doc["last_modified"]
        item["metrics"] = {} #not using what is in stored item for this
        for snap in snaps:
            metric_name = snap["metric_name"]
            item["metrics"][metric_name] = {}
            item["metrics"][metric_name]["values"] = {}
            item["metrics"][metric_name]["values"][snap["created"]] = snap["value"]
            item["metrics"][metric_name]["provenance_url"] = snap["drilldown_url"]
            item["metrics"][metric_name]["static_meta"] = cls.all_static_meta[metric_name]            
        return item

    @classmethod
    def get_simple_item(cls, dao, tiid):
        res = dao.view("by_tiid_with_snaps", 
                startkey=[tiid,0], 
                endkey=[tiid,1])
        rows = res["rows"]
        if not rows:
            return None
        item_doc = rows[0]["value"]
        snaps = [row["value"] for row in rows[1:]]
        item = cls.build_item(item_doc, snaps)
        return item

    @classmethod
    def get_item_object_from_item_doc(cls, dao, item_doc):
        item = Item(dao, id=item_doc["_id"])

        if item_doc is None:
            logger.warning("Unable to load item %s" % id)
            raise LookupError

        item.last_requested = datetime.datetime.now().isoformat()

        # first, just copy everything from the item_doc the DB gave us
        for k in item_doc:
            if k not in ["_id", "_rev"]:
                setattr(item, k, item_doc[k])

        # the aliases property needs to be an Aliases obj, not a dict.
        item.aliases = Aliases(seed=item_doc['aliases'])
        return item



    @classmethod
    def decide_genre(self, alias_dict):
        '''Uses available aliases to decide the item's genre'''

        if "doi" in alias_dict:
            if "10.5061/dryad." in "".join(alias_dict["doi"]):
                return "dataset"
            else:
                return "article"
        elif "pmid" in alias_dict:
            return "article"
        elif "url" in alias_dict:
            joined_urls = "".join(alias_dict["url"])
            if "slideshare.net" in joined_urls:
                return "slides"
            elif "github.com" in joined_urls:
                return "software"
            else:
                return "webpage"
        else:
            return "unknown"

    @classmethod
    def get_metric_names(self, providers_config):
        full_metric_names = []
        providers = ProviderFactory.get_providers(providers_config)
        for provider in providers:
            metric_names = provider.metric_names()
            for metric_name in metric_names:
                full_metric_names.append(provider.provider_name + ':' + metric_name)
        return full_metric_names

    @classmethod
    def make_simple(cls, dao):
        now = datetime.datetime.now().isoformat()
        item = cls.item_class(dao=dao)
        
        # make all the top-level stuff
        item.aliases = Aliases()
        item.biblio = {}
        item.last_modified = now
        item.last_requested = now
        item.created = now

        return item


class CollectionFactory():

    @classmethod
    def make_id(cls, len=6):
        '''Make an id string.

        Currently uses only lowercase and digits for better say-ability. Six
        places gives us around 2B possible values.
        '''
        choices = string.ascii_lowercase + string.digits
        return ''.join(random.choice(choices) for x in range(len))

    @classmethod
    def make(cls, dao, id=None, collection_dict=None):

        if id is not None and collection_dict is not None:
            raise TypeError("you can load from the db or from a dict, but not both")

        now = datetime.datetime.now().isoformat()
        collection = Collection(dao=dao)

        if id is None and collection_dict is None:
            collection.id = cls.make_id()
            collection.created = now
            collection.last_modified = now
        else: # load an extant item
            if collection_dict is None:
                collection_dict = dao.get(id)

            if collection_dict is None:
                raise LookupError
            
            for k in collection_dict:
                setattr(collection, k, collection_dict[k])

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
    #TODO remove the "data" property, bringing this into parallel with teh
    # other stuff in this module.
    
    def __init__(self, seed=None):
        self.data = seed if seed is not None else ""
            
    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self.data)

    def as_dict(self):
        # renamed for consistancy with Items(); TODO cleanup old one
        return self.data


class Aliases(object):
    """
    {
        "title":["Why Most Published Research Findings Are False"],
        "url":["http:\/\/www.plosmedicine.org\/article\/info:doi\/10.1371\/journal.pmed.0020124"],
        "doi": ["10.1371\/journal.pmed.0020124"],
        "created": 12387239847.234,
        "last_modified": 1328569492.406
        ...
    }

    note we're not keeping the TIID in here any more. it needs to be on the the
    item, since that's what it describes. having it in two places == bad.
    """
    
    not_aliases = ["created", "last_modified"]
    
    def __init__(self, seed=None):
        self.created = datetime.datetime.now().isoformat() # will get overwritten if need be
        try:
            for k in seed:
                setattr(self, k, seed[k])
        except TypeError:
            pass

    def add_alias(self, namespace, id):
        try:
            attr = getattr(self, namespace)
            attr.append(id)
        except AttributeError:
            setattr(self, namespace, [id])
        self.last_modified = datetime.datetime.now().isoformat()

    #FIXME: this should take namespace and id, not a list of them
    def add_unique(self, alias_list):
        for ns, id in alias_list:
            if id not in getattr(self, ns, []):
                self.add_alias(ns, id)
        self.last_modified = datetime.datetime.now().isoformat()
    
    def get_aliases_list(self, namespace_list=None): 
        ''' 
        gets list of this object's aliases in each given namespace
        
        returns a list of (namespace, id) tuples
        '''
        # if this is a get on everything, just summon up the items
        if namespace_list is None:
            namespace_list = self.get_namespace_list()
        
        # if the caller doesn't pass us a list, but just a single value, wrap it
        # up for them
        if not hasattr(namespace_list, "append"):
            namespace_list = [namespace_list]
        
        # otherwise, get for the specific namespaces
        ret = []
        for namespace in namespace_list:
            try:
                ids = getattr(self, namespace)
            
                # crazy hack TODO fix lists/strings flying about
                if not hasattr(ids, "append"):
                    ids = [ids]
                ret += [(namespace, id) for id in ids]
            except AttributeError:
                # this alias doesn't have that namespace...no worries, move on.
                pass

        return ret

    def get_namespace_list(self):
        return [x for x in self.__dict__ if x not in self.not_aliases]

    def clear_aliases(self):
        # Wipe out the aliases and set last_modified. This should be used
        # when an alias update has failed, so that we can dequeue the item
        # without then going on to process metrics incorrectly.
        for attr in self.get_namespace_list():
            delattr(self, attr)
        self.last_modified = datetime.datetime.now().isoformat()

    # FIXME I don't think we need this any more?
    def as_dict(self):
        return self.__dict__

# could make these saveable into the DB if we wanted, in the future
class Error():
    pass

