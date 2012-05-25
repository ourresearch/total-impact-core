from werkzeug import generate_password_hash, check_password_hash
import totalimpact.dao as dao
from totalimpact import default_settings
from totalimpact.providers.provider import ProviderFactory
import time, uuid, json, hashlib, inspect, re, copy, string, random

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
        start_time = time.time()
        dict_repr = todict(self,ignore=['dao'])
        return dict_repr

    def _update_dict(self, input, my_dict=None):
        '''Use another dict to recursively add list or dict items not in this.
        
        This object's value wins all conflicts, but new values in lists and 
        dictionaries are added. Used to update from the db before saving.
        I think this might should go in the dao...not sure.

        returns - dict
        '''
        if my_dict is None:
            my_dict = self.as_dict()

        if input is None:
            return my_dict

        for k, v in input.iteritems():
            try:
                #get the dict here...whenever
                
                new_my_dict = my_dict.setdefault(k, {})
                self._update_dict(v, new_my_dict)

            except AttributeError, e:
                if not my_dict[k]:
                    my_dict[k] = v
        
        return my_dict

    def save(self):
        """ Save the object to the database, handling merging of data 
            should the object have already been updated elsewhere """
        # Blocking call to acquire a lock for this section
        retry = True
        import couchdb

        # Get the lock for this item for write
        lock = itemlock.getItemLock(self.id)
        lock.acquire()
        while retry:
            try:
                # Find the current state of the item in the database
                # which we will update
                new_dict = self.dao.get(self.id)
                dict_to_save = self._update_dict(new_dict)
                # If we are updating an object, then we should
                # set _rev from the object we have just read so
                # we don't get conflict errors on commit.
                if new_dict:
                    dict_to_save['_rev'] = new_dict['_rev']
                res = self.dao.save_and_commit(dict_to_save)
                retry = False
            except couchdb.ResourceConflict, e:
                logger.info("Couch conflict, will retry")
        lock.release()

        return res

    def delete(self):
        self.dao.delete(self.id)
        return True


class Item(Saveable):
    pass


class ItemFactory():
    #TODO this should subclass a SaveableFactory

    item_class = Item

    @classmethod
    def get(cls, dao, id, provider_maker, providers_config):
        now = time.time()
        item_doc = dao.get(id)
        item = cls.item_class(dao, id=id)

        if item_doc is None:
            logger.warning("Unable to load item %s" % id)
            raise LookupError

        item.last_requested = now

        # first, just copy everything from the item_doc the DB gave us
        for k in item_doc:
            if k not in ["_id", "_rev"]:
                setattr(item, k, item_doc[k])

        # the aliases property needs to be an Aliases obj, not a dict.
        item.aliases = Aliases(seed=item_doc['aliases'])

        # determine and set the item's genre
        item.biblio['genre'] = cls.decide_genre(item_doc['aliases'])

        # make the Metric objects. We have to make keys for each metric in the config
        # so that Providers will know which metrics to update later on.
        # Then we fill these Metric objects's dictionaries with the metricSnaps
        # from the db.

        item.metrics = {}
        metric_names = cls.get_metric_names(providers_config)
        for full_metric_name in metric_names:
            try:
                my_metric = item_doc["metrics"][full_metric_name]
            except KeyError: #this metric ain't in the item_doc from the db
                my_metric = {'values': {} }
            
            (provider_name, metric_name) = full_metric_name.split(":")

            # make the provenance url
            # FIXME problem if alias needed for provenance url not obtained yet?
            aliases_list = item.aliases.get_aliases_list()
            provider = provider_maker(provider_name)

            provenance_url = provider.provenance_url(metric_name, aliases_list)
            my_metric["provenance_url"] = provenance_url

            # populate the static_meta only if it has a provenance url
            if provenance_url:
                my_metric["static_meta"] = {}
                if provider.provides_static_meta:
                    my_metric["static_meta"] = provider.static_meta(metric_name)

            item.metrics[full_metric_name] = my_metric

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
    def make(cls, dao, providers_config):
        now = time.time()
        item = cls.item_class(dao=dao)
        
        # make all the top-level stuff
        item.aliases = Aliases()
        item.metrics = {}
        item.biblio = {}
        item.last_modified = now
        item.last_requested = now
        item.last_queued = None
        item.created = now

        # make the metrics objects. We have to make all the ones in the config
        # so that Providers will know which ones to update later on.
        metric_names = cls.get_metric_names(providers_config)
        for name in metric_names:
            item.metrics[name] = {'values': {} }

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

        now = time.time()
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
        except AttributeError:
            setattr(self, namespace, [id])
        self.last_modified = time.time()

    #FIXME: this should take namespace and id, not a list of them
    def add_unique(self, alias_list):
        for ns, id in alias_list:
            if id not in getattr(self, ns, []):
                self.add_alias(ns, id)
        self.last_modified = time.time()
    
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
        self.last_modified = time.time()

    # FIXME I don't think we need this any more?
    def as_dict(self):
        return self.__dict__

# could make these saveable into the DB if we wanted, in the future
class Error():
    pass

