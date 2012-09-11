from werkzeug import generate_password_hash, check_password_hash
from couchdb import ResourceNotFound, ResourceConflict
import shortuuid, datetime, hashlib, threading, json, time, copy

from totalimpact.providers.provider import ProviderFactory
from totalimpact.providers.provider import ProviderTimeout
from totalimpact import default_settings
from totalimpact.utils import Retry

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.models')

class NotAuthenticatedError(Exception):
    pass


def closest(target, collection) :
    return min((abs(target - i), i) for i in collection)[1]

class ItemFactory():

    all_static_meta = ProviderFactory.get_all_static_meta()


    @classmethod
    def get_item(cls, tiid, myrefsets, dao):
        res = dao.view("queues/by_tiid_with_snaps")
        rows = res[[tiid,0]:[tiid,"zzzzzzzzzzzzzz"]].rows

        if not rows:
            return None
        else:
            item = rows[0]["value"]
            most_recent_snaps = {}
            for row in rows[1:]:
                snap = row["value"]
                # they are in reverse order of creation, so overwrite
                # and most recent one will be on top.
                most_recent_snaps[snap["metric_name"]] = snap

            snaps = most_recent_snaps.values()

            try:
                item = cls.build_item_for_client(item, snaps, myrefsets)
            except Exception, e:
                item = None
                logger.error("Exception %s: Unable to build item %s, %s, %s" % (e.__repr__(), tiid, str(item), str(snaps)))
                raise
        return item

    @classmethod
    def build_item_for_client(cls, item, snaps, myrefsets):
        item["biblio"]['genre'] = cls.decide_genre(item['aliases'])
           
        item["metrics"] = {} #not using what is in stored item for this

        # need year to calculate normalization below
        try:
            year = item["biblio"]["year"]
        except KeyError:
            year = 99 # hack so that it won't match anything.  what else to do?

        if year < 2002:
            year = 2002

        for snap in snaps:
            metric_name = snap["metric_name"]
            if metric_name in cls.all_static_meta.keys():
                item["metrics"][metric_name] = {}
                item["metrics"][metric_name]["values"] = {}
                item["metrics"][metric_name]["provenance_url"] = snap["drilldown_url"]
                item["metrics"][metric_name]["static_meta"] = cls.all_static_meta[metric_name]            
                item["metrics"][metric_name]["values"]["raw"] = snap["value"]
                normalized_values = cls.get_normalized_values(item["biblio"]['genre'], year, metric_name, snap["value"], myrefsets)
                item["metrics"][metric_name]["values"].update(normalized_values)

        return item

    @classmethod
    def build_snap(cls, tiid, metric_value_drilldown, metric_name):

        now = datetime.datetime.now().isoformat()
        # if the alphabet below changes, need to update couch queue lookups        
        shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')

        snap = {}
        snap["_id"] = shortuuid.uuid()[0:24]
        snap["type"] = "metric_snap"
        snap["metric_name"] = metric_name
        snap["tiid"] = tiid
        snap["created"] = now
        (value, drilldown_url) = metric_value_drilldown
        snap["value"] = value
        snap["drilldown_url"] = drilldown_url
        return snap

    @classmethod
    def add_snap(cls, item, snap):
        """Adds a metrics snap to an item, and returns the item

        Snaps must have keys "metric_name", "timestamp," and "value"
        """

        metrics = item.setdefault("metrics", {})
        this_metric = metrics.setdefault(snap["metric_name"], {})
        this_metric[snap["timestamp"]] = snap["value"]

        return item

    @classmethod
    def make(cls):

        now = datetime.datetime.now().isoformat()
        # if the alphabet below changes, need to update couch queue lookups
        shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')

        item = {}
        item["_id"] = shortuuid.uuid()[0:24]
        item["aliases"] = {}
        item["biblio"] = {}
        item["last_modified"] = now
        item["created"] = now
        item["type"] = "item"
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
        elif "github" in alias_dict:
            return "software"
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
    def alias_tuples_from_dict(self, aliases_dict):
        """
        Convert from aliases dict we use in items, to a list of alias tuples.

        The providers need the tuples list, which look like this:
        [(doi, 10.123), (doi, 10.345), (pmid, 1234567)]
        """
        alias_tuples = []
        for ns, ids in aliases_dict.iteritems():
            if isinstance(ids, basestring): # it's a date, not a list of ids
                alias_tuples.append((ns, ids))
            else:
                for id in ids:
                    alias_tuples.append((ns, id))
        return alias_tuples

    @classmethod
    def alias_dict_from_tuples(self, aliases_tuples):
        alias_dict = {}
        for (ns, ids) in aliases_tuples:
            if ns in alias_dict:
                alias_dict[ns] += [ids]
            else:
                alias_dict[ns] = [ids]
        return alias_dict

    @classmethod
    def merge_alias_dicts(self, aliases1, aliases2):
        #logger.debug("in MERGE ALIAS DICTS with %s and %s" %(aliases1, aliases2))
        merged_aliases = copy.deepcopy(aliases1)
        for ns, nid in aliases2.iteritems():
            try:
                merged_aliases[ns].append(nid)
                merged_aliases[ns] = list(set(aliases2[ns]))
            except KeyError: # no ids for that namespace yet. make it.
                merged_aliases[ns] = nid
            except AttributeError:
                # nid is a string; overwrite.
                merged_aliases[ns] = nid
                logger.debug("aliases[{ns}] is a string ('{nid}'); overwriting".format(
                    ns=ns, nid=nid))
        return merged_aliases

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
    def get_normalized_values(cls, genre, year, metric_name, value, myrefsets):
        # Will be passed None as myrefsets type when loading items in reference collections :)
        if not myrefsets:
            return {}

        # for now, only normalize articles
        if genre != "article":
            return {}

        # treat the f1000 "Yes" as a 1 for normalization
        if value=="Yes":
            value = 1

        response = {}
        for refsetname in myrefsets:
            try:
                fencepost_values = myrefsets[refsetname][str(year)][metric_name].keys()
                myclosest = closest(value, fencepost_values)
                response[refsetname] = myrefsets[refsetname][str(year)][metric_name][myclosest]
            except KeyError:
                #logger.info("No good lookup in %s %s for %s" %(refsetname, str(year), metric_name))
                pass
                
        return response

    @classmethod
    def retrieve_items(cls, tiids, myrefsets, myredis, mydao):
        something_currently_updating = False
        items = []
        for tiid in tiids:
            try:
                item = cls.get_item(tiid, myrefsets, mydao)
            except (LookupError, AttributeError), e:
                logger.warning("Got an error looking up tiid '{tiid}'; error: {error}".format(
                        tiid=tiid, error=e.__repr__()))
                raise

            if not item:
                logger.warning("Looks like there's no item with tiid '{tiid}': ".format(
                        tiid=tiid))
                raise LookupError
                
            item["currently_updating"] = cls.is_currently_updating(tiid, myredis)
            something_currently_updating = something_currently_updating or item["currently_updating"]

            items.append(item)
        return (items, something_currently_updating)

    @classmethod
    def is_currently_updating(cls, tiid, myredis):
        num_providers_left = myredis.get_num_providers_left(tiid)
        if num_providers_left:
            currently_updating = myredis.get_num_providers_left(tiid) > 0
        else: # not in redis, maybe because it expired.  Assume it is not currently updating.
            currently_updating = False        
        return currently_updating


class MemberItems():

    def __init__(self, provider, redis):
        self.provider = provider
        self.redis = redis

    def start_update(self, str):
        pages = self.provider.paginate(str)
        hash = hashlib.md5(str.encode('utf-8')).hexdigest()
        t = threading.Thread(target=self._update, 
                            args=(pages, hash), 
                            name=hash[0:4]+"_memberitems_thread")
        t.daemon = True
        t.start()
        return hash

    def get_sync(self, query):
        ret = {}
        start = time.time()
        ret = {
            "memberitems": self.provider.member_items(query),
            "pages": 1,
            "complete": 1
        }
        logger.debug("got {num_memberitems} synchronous memberitems for query '{query}' in {elapsed} seconds.".format(
            num_memberitems=len(ret["memberitems"]),
            query=query,
            elapsed=round(time.time() - start, 2)
        ))
        return ret

    def get_async(self, query_hash):
        query_status_str = self.redis.get(query_hash)
        start = time.time()

        try:
            ret = json.loads(query_status_str)
        except TypeError:
            # if redis returns None, the update hasn't started yet (likely still
            # parsing the input string; give the client some information, though:
            ret = {"memberitems": [], "pages": 1, "complete": 0 }

        logger.debug("have finished {num_memberitems} asynchronous memberitems for query hash '{query_hash}' in {elapsed} seconds.".format(
                num_memberitems=len(ret["memberitems"]),
                query_hash=query_hash,
                elapsed=round(time.time() - start, 2)
            ))

        return ret

    @Retry(3, ProviderTimeout, 0.1)
    def _update(self, pages, key):

        status = {
            "memberitems": [],
            "pages": len(pages),
            "complete": 0
        }
        for page in pages:
            status["memberitems"].append(self.provider.member_items(page))
            status["complete"] += 1
            self.redis.set(key, json.dumps(status))

        return True

class UserFactory():


    @classmethod
    def get(cls, id, dao, key):
        try:
            print id
            doc = dao.db[id]
            print dict(doc)
        except ResourceNotFound:
            raise KeyError("User doesn't exist.")

        else:
            if doc["key"] == key:
                return doc
            else:
                raise NotAuthenticatedError


    @classmethod
    def put(cls, userdict,  password, dao):

        if "_id" not in userdict.keys() or "colls" not in userdict.keys():
            raise AttributeError

        try:
            doc = cls.get(userdict["_id"], dao, password)
            userdict["_rev"] = doc["_rev"]
        except KeyError:
            pass # no worries, we'll just make a new user.

        userdict["type"] = "user"
        dao.db.save(userdict)
        return userdict


