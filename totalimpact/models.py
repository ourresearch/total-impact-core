from werkzeug import generate_password_hash, check_password_hash
from couchdb import ResourceNotFound, ResourceConflict
import shortuuid, datetime, hashlib, threading, json, time, copy, re

from totalimpact.providers.provider import ProviderFactory
from totalimpact.providers.provider import ProviderTimeout, ProviderServerError
from totalimpact import default_settings
from totalimpact.utils import Retry

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.models')

# setup to remove control characters from received IDs
# from http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

class NotAuthenticatedError(Exception):
    pass

def largest_value_that_is_less_than_or_equal_to(target, collection):
    collection_as_numbers = [(int(i), i) for i in collection if int(i) <= target]
    return max(collection_as_numbers)[1]

class ItemFactory():

    all_static_meta = ProviderFactory.get_all_static_meta()


    @classmethod
    def clean_id(cls, nid):

        nid = control_char_re.sub('', nid)
        nid = nid.replace(u'\u200b', "")
        nid = nid.strip()
        return(nid)

    @classmethod
    def get_item(cls, tiid, myrefsets, dao, include_history=False):
        item_doc = dao.get(tiid)
        if not item_doc:
            return None
        try:
            item = cls.build_item_for_client(item_doc, myrefsets, include_history)
        except Exception, e:
            item = None
            logger.error("Exception %s: Skipping item, unable to build %s, %s" % (e.__repr__(), tiid, str(item)))
        return item

    @classmethod
    def build_item_for_client(cls, item, myrefsets, include_history=False):

        try:
            (genre, host) = cls.decide_genre(item['aliases'])
            item["biblio"]['genre'] = genre
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

            #delete the raw history from what we return to the client for now
            if not include_history:
                try:
                    del metrics[metric_name]["values"]["raw_history"]
                except KeyError:
                    pass

            if metric_name in cls.all_static_meta.keys():  # make sure we still support this metrics type

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
        genre = "unknown"
        host = "unknown"

        '''Uses available aliases to decide the item's genre'''
        if "doi" in alias_dict:
            joined_doi_string = "".join(alias_dict["doi"])
            joined_doi_string = joined_doi_string.lower()
            if "10.5061/dryad." in joined_doi_string:
                genre = "dataset"
                host = "dryad"
            elif ".figshare." in joined_doi_string:
                genre = "dataset"
                host = "figshare"
            else:
                genre = "article"

        elif "pmid" in alias_dict:
            genre = "article"

        elif "github" in alias_dict:
            genre = "software"
            host = "github"

        elif "url" in alias_dict:
            joined_url_string = "".join(alias_dict["url"])
            joined_url_string = joined_url_string.lower()
            if "slideshare.net" in joined_url_string:
                genre = "slides"
                host = "slideshare"
            elif "github.com" in joined_url_string:
                genre = "software"
                host = "github"
            else:
                genre = "webpage"
                host = "webpage"

        return (genre, host)

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

    @classmethod
    def create_or_update_items_from_aliases(cls, aliases, myredis, mydao):
        logger.info("got a list of aliases; creating new items for them.")
        try:
            # remove unprintable characters and change list to tuples
            clean_aliases = [(cls.clean_id(namespace), cls.clean_id(nid)) for [namespace, nid] in aliases]
        except ValueError:
            logger.error("bad input to POST /collection (requires [namespace, id] pairs):{input}".format(
                    input=str(aliases)
                ))
            return None

        logger.debug("POST /collection got list of aliases; create or find items for {aliases}".format(
                aliases=str(clean_aliases)
            ))

        (tiids, new_items) = cls.create_or_find_items_from_aliases(clean_aliases, myredis, mydao)

        logger.debug("POST /collection included {num} new items: {new_items}".format(
                num=len(new_items),
                new_items=str(new_items)
            ))

        # batch upload the new docs to the db
        # make sure they are there before the provider updates start happening
        for doc in mydao.db.update(new_items):
            pass

        # for each item, set the number of providers that need to run before the update is done
        # and put them on the update queue
        for item in new_items:
            myredis.set_num_providers_left(
                item["_id"],
                ProviderFactory.num_providers_with_metrics(
                    default_settings.PROVIDERS)
            )
            myredis.add_to_alias_queue(item["_id"], item["aliases"])

        return tiids

    @classmethod
    def create_item(cls, namespace, nid, myredis, mydao):
        logger.debug("In create_item with alias" + str((namespace, nid)))
        item = ItemFactory.make()

        # set this so we know when it's still updating later on
        myredis.set_num_providers_left(
            item["_id"],
            ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
        )

        item["aliases"][namespace] = [nid]
        mydao.save(item)

        myredis.add_to_alias_queue(item["_id"], item["aliases"])

        logger.info("Created new item '{id}' with alias '{alias}'".format(
            id=item["_id"],
            alias=str((namespace, nid))
        ))

        try:
            return item["_id"]
        except AttributeError:
            abort(500)

    @classmethod
    def create_or_find_items_from_aliases(cls, clean_aliases, myredis, mydao):
        tiids = []
        new_items = []
        for alias in clean_aliases:
            (namespace, nid) = alias
            existing_tiid = cls.get_tiid_by_alias(namespace, nid, myredis, mydao)
            if existing_tiid:
                tiids.append(existing_tiid)
                logger.debug("found an existing tiid ({tiid}) for alias {alias}".format(
                        tiid=existing_tiid,
                        alias=str(alias)
                    ))
            else:
                logger.debug("alias {alias} isn't in the db; making a new item for it.".format(
                        alias=alias
                    ))
                item = ItemFactory.make()
                item["aliases"][namespace] = [nid]

                new_items.append(item)
                tiids.append(item["_id"]) 

        # could be duplicate tiids if two aliases were synonymns. Return list of uniques
        unique_tiids = list(set(tiids))
        return(unique_tiids, new_items)

    @classmethod
    def create_item_from_namespace_nid(cls, namespace, nid, myredis, mydao):
        # remove unprintable characters
        nid = ItemFactory.clean_id(nid)

        tiid = cls.get_tiid_by_alias(namespace, nid, myredis, mydao)
        if tiid:
            logger.debug("... found with tiid " + tiid)
        else:
            tiid = cls.create_item(namespace, nid, myredis, mydao)
            logger.debug("new item created with tiid " + tiid)

        return tiid

    @classmethod
    def get_tiid_by_alias(cls, ns, nid, myredis, mydao):
        res = mydao.view('queues/by_alias')

        # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults# for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
        logger.debug("In get_tiid_by_alias with {ns}, {nid}".format(
            ns=ns, nid=nid))
        nid_lower = nid.lower()
        logger.debug("In get_tiid_by_alias with {nid_lower}".format(
            nid_lower=nid_lower))

        # not lower now
        matches = res[[ns, 
                        nid]] 

        if matches.rows:
            if len(matches.rows) > 1:
                logger.warning("More than one tiid for alias (%s, %s)" % (ns, nid))
            tiid = matches.rows[0]["id"]
            logger.debug("found a match for {nid}!".format(nid=nid))
        else:
            logger.debug("no match for {nid}!".format(nid=nid))
            tiid = None
        return tiid

    @classmethod
    def start_item_update(cls, tiids, myredis, mydao, sleep_in_seconds=0):
        # put each of them on the update queue
        for tiid in tiids:
            logger.debug("In start_item_update with tiid " + tiid)

            # set this so we know when it's still updating later on
            myredis.set_num_providers_left(
                tiid,
                ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
            )

            item_doc = mydao.get(tiid)
            try:
                myredis.add_to_alias_queue(item_doc["_id"], item_doc["aliases"])
            except (KeyError, TypeError):
                logger.debug("couldn't get item_doc for {tiid}. Skipping its update".format(
                    tiid=tiid))
                pass

            time.sleep(sleep_in_seconds)


class MemberItems():

    def __init__(self, provider, redis):
        self.provider = provider
        self.redis = redis

    def start_update(self, str):
        paginate_dict = self.provider.paginate(str)
        hash = hashlib.md5(str.encode('utf-8')).hexdigest()
        t = threading.Thread(target=self._update, 
                            args=(paginate_dict["pages"], paginate_dict["number_entries"], hash), 
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
            "complete": 1,
            "error": False
        }
        ret["number_entries"] = len(ret["memberitems"])

        logger.debug("got {number_finished_memberitems} synchronous memberitems for query '{query}' in {elapsed} seconds.".format(
            number_finished_memberitems=len(ret["memberitems"]),
            query=query,
            elapsed=round(time.time() - start, 2)
        ))
        return ret

    def get_async(self, query_hash):
        query_status = self.redis.get_memberitems_status(query_hash)
        start = time.time()

        if not query_status:
            query_status = {"memberitems": [], "pages": 1, "complete": 0, "error": False} # don't know number_entries yet

        logger.debug("have finished {number_finished_memberitems} of asynchronous memberitems for query hash '{query_hash}' in {elapsed} seconds.".format(
                number_finished_memberitems=len(query_status["memberitems"]),
                query_hash=query_hash,
                elapsed=round(time.time() - start, 2)
            ))

        return query_status


    @Retry(3, ProviderTimeout, 0.1)
    def _update(self, pages, number_entries, query_key):

        status = {
            "memberitems": [],
            "pages": len(pages),
            "complete": 0,
            "number_entries": number_entries,
            "error": False            
        }
        self.redis.set_memberitems_status(query_key, status)
        for page in pages:
            try:
                memberitems = self.provider.member_items(page)
                status["memberitems"].append(memberitems)
            except (ProviderTimeout, ProviderServerError):
                status["error"] = True
            status["complete"] += 1
            self.redis.set_memberitems_status(query_key, status)

        return True

class UserFactory():


    @classmethod
    def get(cls, id, dao, key):
        try:
            doc = dao.db[id]
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


