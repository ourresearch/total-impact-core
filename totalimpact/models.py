from werkzeug import generate_password_hash, check_password_hash
from totalimpact.providers.provider import ProviderFactory
from totalimpact import default_settings
from totalimpact.pidsupport import Retry
from couchdb import ResourceNotFound, ResourceConflict
from totalimpact.providers.provider import ProviderTimeout
import shortuuid, string, random, datetime, hashlib, threading, json, time

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.models')

class NotAuthenticatedError(Exception):
    pass

class ItemFactory():

    all_static_meta = ProviderFactory.get_all_static_meta()


    @classmethod
    def get_item(cls, dao, tiid):
        res = dao.view("queues/by_tiid_with_snaps")
        rows = res[[tiid,0]:[tiid,1]].rows

        if not rows:
            return None
        else:
            item = rows[0]["value"]
            snaps = [row["value"] for row in rows[1:]]
            try:
                item = cls.build_item_for_client(item, snaps)
            except Exception, e:
                item = None
                logger.error("Exception %s: Unable to build item %s, %s, %s" % (e.__repr__(), tiid, str(item), str(snaps)))
        return item

    @classmethod
    def build_item_for_client(cls, item, snaps):
        item["biblio"]['genre'] = cls.decide_genre(item['aliases'])

            
        item["metrics"] = {} #not using what is in stored item for this
        for snap in snaps:
            metric_name = snap["metric_name"]
            if metric_name in cls.all_static_meta.keys():
                item["metrics"][metric_name] = {}
                item["metrics"][metric_name]["values"] = {}
                item["metrics"][metric_name]["values"][snap["created"]] = snap["value"]
                item["metrics"][metric_name]["provenance_url"] = snap["drilldown_url"]
                item["metrics"][metric_name]["static_meta"] = cls.all_static_meta[metric_name]            
        return item
    


    @classmethod
    def build_snap(cls, tiid, metric_value_drilldown, metric_name):

        now = datetime.datetime.now().isoformat()
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
    def make(cls):

        now = datetime.datetime.now().isoformat()
        shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')

        item = {}
        item["_id"] = shortuuid.uuid()[0:24]
        item["aliases"] = {}
        item["biblio"] = {}
        item["last_modified"] = now
        item["created"] = now
        item["type"] = "item"
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
    def get_titles(cls, cids, dao):
        ret = {}
        for cid in cids:
            coll = dao.db[cid]
            ret[cid] = coll["title"]

        return ret



    @classmethod
    def make(cls, owner=None):

        key, key_hash = cls._make_update_keypair()

        now = datetime.datetime.now().isoformat()
        collection = {}

        collection["_id"] = cls._make_id()
        collection["created"] = now
        collection["last_modified"] = now
        collection["type"] = "collection"
        collection["key_hash"] = key_hash
        collection["owner"] = owner

        return collection, key

    @classmethod
    def claim_collection(cls, coll, new_owner, key):
        if "key_hash" not in coll.keys():
            raise ValueError("This is an old collection that doesnt' support ownership.")
        elif check_password_hash(coll["key_hash"], key):
            coll["owner"] = new_owner
            return coll
        else:
            raise ValueError("The given key doesn't match this collection's key")

    @classmethod
    def _make_id(cls, len=6):
        '''Make an id string.

        Currently uses only lowercase and digits for better say-ability. Six
        places gives us around 2B possible values.
        '''
        choices = string.ascii_lowercase + string.digits
        return ''.join(random.choice(choices) for x in range(len))

    @classmethod
    def _make_update_keypair(cls):
        key = shortuuid.uuid()
        key_hash = generate_password_hash(key)
        return key, key_hash

    @classmethod
    def get(cls, dao, myredis, cid):
        """
        Gets a collection dict from the db; formatting done by other methods
        """
        logger.info("getting collection for cid" + cid)
        res = dao.db.view("queues/collections-with-items", include_docs=True)
        try:
            coll = dict([row.doc for row in res[[cid, 0]]][0])
        except IndexError:
            # key error makes more sense for client code
            logger.error("Collection '{cid}' not found.".format(cid=cid))
            raise KeyError("Collection '{cid}' not found.".format(cid=cid))
        coll["items"]= []
        items_currently_updating = 0
        for row in res[[cid, 1]]:
            currently_updating = myredis.get_num_providers_left(row["id"]) > 0 # boolean
            row["doc"]["currently_updating"] = currently_updating
            items_currently_updating += int(currently_updating)
            coll["items"].append(row["doc"])

        coll["num_items_updating"] = items_currently_updating
        return coll

    @classmethod
    def get_json(cls, dao, myredis, cid):
        coll = cls.get(dao, myredis, cid)
        return json.dumps(coll, sort_keys=True, indent=4), coll["num_items_updating"]

    @classmethod
    def get_csv(cls, dao, myredis, cid):
        coll = cls.get(dao, myredis, cid)

        # create the header row
        header_metric_names = []
        for item in coll["items"]:
            header_metric_names += item["metrics"].keys()

            # get unique
            header_alias_names = ["title", "doi"]
            header_metric_names = sorted(list(set(header_metric_names)))

            csv_list = ["tiid," + ','.join(header_alias_names + header_metric_names)]

        # body rows
        for item in coll["items"]:
            column_list = [item["_id"]]
            for alias_name in header_alias_names:
                try:
                    value_to_store = item['aliases'][alias_name][0]
                    if (" " in value_to_store) or ("," in value_to_store):
                        value_to_store = '"' + value_to_store + '"'
                    column_list += [value_to_store]
                except (IndexError, KeyError):
                    column_list += [""]
            for metric_name in header_metric_names:
                try:
                    values = item['metrics'][metric_name]['values']
                    latest_key = sorted(values, reverse=True)[0]
                    value_to_store = str(values[latest_key])
                    if (" " in value_to_store) or ("," in value_to_store):
                        value_to_store = '"' + value_to_store + '"'
                    column_list += [value_to_store]
                except (IndexError, KeyError):
                    column_list += [""]
            csv_list.append(",".join(column_list))

        # join together in a string
        csv = "\n".join(csv_list)
        return csv, coll["num_items_updating"]


class MemberItems():

    def __init__(self, provider, redis):
        self.provider = provider
        self.redis = redis

    def start_update(self, str):
        pages = self.provider.paginate(str)
        hash = hashlib.md5(str.encode('utf-8')).hexdigest()
        t = threading.Thread(target=self._update, args=(pages, hash))
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
            return False

        try:
            doc = cls.get(userdict["_id"], dao, password)
        except KeyError:
            doc = None # no worries, we'll just make the user.

        # we mostly overwrite, but want to merge in the server's colls
        if doc is not None:
            userdict["colls"] = dict(doc["colls"].items() + userdict["colls"].items())
            userdict["_rev"] = doc["_rev"]

        userdict["type"] = "user"
        dao.db.save(userdict)
        return userdict


