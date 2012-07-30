from werkzeug import generate_password_hash, check_password_hash
from totalimpact.providers.provider import ProviderFactory
import uuid, string, random, datetime, iso8601, pytz

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.models')


class ItemFactory():

    all_static_meta = ProviderFactory.get_all_static_meta()


    @classmethod
    def get_item(cls, dao, tiid):
        res = dao.view("queues/by_tiid_with_snaps")
        rows = res[[tiid,0]:[tiid,1]].rows

        if not rows:
            return None
        else:
            item_doc = rows[0]["value"]
            snaps = [row["value"] for row in rows[1:]]
            try:
                item = cls.build_item_for_client(item_doc, snaps)
            except Exception, e:
                item = None
                logger.error("Exception %s: Unable to build item %s, %s, %s" % (e, tiid, str(item_doc), str(snaps)))
        return item

    @classmethod
    def build_item_for_client(cls, item_doc, snaps):
        item = {}
        item["id"] = item_doc["_id"]
        item["biblio"]['genre'] = cls.decide_genre(item_doc['aliases'])
        item["currently_updating"] = (item["currently_updating"] != item["providersWithMetricsCount"])

            
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
    def build_snap(cls, tiid, metric_value_drilldown, metric_name):
        snap = {}
        snap["type"] = "metric_snap"
        snap["metric_name"] = metric_name
        snap["tiid"] = tiid
        snap["created"] = datetime.datetime.now().isoformat()
        (value, drilldown_url) = metric_value_drilldown
        snap["value"] = value
        snap["drilldown_url"] = drilldown_url
        return snap        

    @classmethod
    def make_new_item(cls):
        item = {}
        
        # make all the top-level stuff
        now = datetime.datetime.now().isoformat()
        item["aliases"] = Aliases()
        item["biblio"] = {}
        item["last_modified"] = now
        item["created"] = now
        item["type"] = "item"
        item["providersRunCounter"] = 0
        item["providersWithMetricsCount"] = ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)

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
            collection.type = "collection"
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

