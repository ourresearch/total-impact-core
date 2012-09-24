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


def largest_value_that_is_less_than_or_equal_to(target, collection):
    collection_as_numbers = [(int(i), i) for i in collection if int(i) <= target]
    return max(collection_as_numbers)[1]

class ItemFactory():

    all_static_meta = ProviderFactory.get_all_static_meta()

    @classmethod
    def get_item(cls, tiid, myrefsets, dao):
        item_doc = dao.get(tiid)
        if not item_doc:
            return None
        try:
            item = cls.build_item_for_client(item_doc, myrefsets)
        except Exception, e:
            item = None
            logger.error("Exception %s: Skipping item, unable to build %s, %s" % (e.__repr__(), tiid, str(item)))
        return item

    @classmethod
    def build_item_for_client(cls, item, myrefsets):
        try:
            item["biblio"]['genre'] = cls.decide_genre(item['aliases'])
        except (KeyError, TypeError):
            logger.error("Skipping item, unable to lookup aliases or biblio in %s" % str(item))
            return None

        # need year to calculate normalization below
        try:
            year = item["biblio"]["year"]
            if year < 2002:
                year = 2002
        except KeyError:
            year = 99 # hack so that it won't match anything.  what else to do?

        metrics = item.setdefault("metrics", {})
        for metric_name in metrics:
            if metric_name in cls.all_static_meta.keys():  # make sure we still support this metrics type
                #delete the raw history from what we return to the client for now
                try:
                    del metrics[metric_name]["values"]["raw_history"]
                except KeyError:
                    pass

                # add static data
                metrics[metric_name]["static_meta"] = cls.all_static_meta[metric_name]            

                # add normalization values
                raw = metrics[metric_name]["values"]["raw"]
                normalized_values = cls.get_normalized_values(item["biblio"]['genre'], year, metric_name, raw, myrefsets)

                metrics[metric_name]["values"].update(normalized_values)

        return item

    @classmethod
    def add_metrics_data(cls, metric_name, metrics_method_response, item):
        metrics = item.setdefault("metrics", {})
        
        (metric_value, provenance_url) = metrics_method_response

        this_metric = metrics.setdefault(metric_name, {})
        this_metric["provenance_url"] = provenance_url

        this_metric_values = this_metric.setdefault("values", {})
        this_metric_values["raw"] = metric_value

        this_metric_values_raw_history = this_metric_values.setdefault("raw_history", {})
        now = datetime.datetime.now().isoformat()
        this_metric_values_raw_history[now] = metric_value
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
    def clean_for_export(cls, item, supplied_key=None, secret_key=None):
        if supplied_key:
            if supplied_key == secret_key:
                return(item)

        # if still here, then need to remove sensitive data
        cleaned_item = copy.deepcopy(item)
        metrics = cleaned_item.setdefault("metrics", {})
        metric_names = metrics.keys()
        for metric_name in metric_names:
            if "scopus:" in metric_name:
                del cleaned_item["metrics"][metric_name]
        return cleaned_item


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
        for ns, nid_list in aliases2.iteritems():
            for nid in nid_list:
                try:
                    if not nid in merged_aliases[ns]:
                        merged_aliases[ns].append(nid)
                except KeyError: # no ids for that namespace yet. make it.
                    merged_aliases[ns] = [nid]
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

        if genre not in myrefsets.keys():
            #logger.info("Genre {genre} not in refsets so give up".format(
            #    genre=genre))
            return {}

        # treat the f1000 "Yes" as a 1 for normalization
        if value=="Yes":
            value = 1

        response = {}
        for refsetname in myrefsets[genre]:
            # year is a number
            try:
                fencepost_values = myrefsets[genre][refsetname][int(year)][metric_name].keys()
                myclosest = largest_value_that_is_less_than_or_equal_to(value, fencepost_values)
                response[refsetname] = myrefsets[genre][refsetname][int(year)][metric_name][myclosest]
            except KeyError:
                #logger.info("No good lookup in %s %s %s for %s" %(genre, refsetname, year, metric_name))
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


