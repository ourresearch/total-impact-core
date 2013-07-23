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
logger = logging.getLogger('ti.item')

# setup to remove control characters from received IDs
# from http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

class NotAuthenticatedError(Exception):
    pass

def largest_value_that_is_less_than_or_equal_to(target, collection):
    collection_as_numbers = [(int(i), i) for i in collection if int(i) <= target]
    if collection_as_numbers:
        response = max(collection_as_numbers)[1]
    else:
        # the value is lower than anything we've seen before, so return lowest value
        response = min([(int(i), i) for i in collection])[1]
    return response

all_static_meta = ProviderFactory.get_all_static_meta()



def clean_id(nid):
    try:
        nid = control_char_re.sub('', nid)
        nid = nid.replace(u'\u200b', "")
        nid = nid.strip()
    except TypeError:
        #isn't a string.  That's ok, might be biblio
        pass
    return(nid)

def get_item(tiid, myrefsets, dao, include_history=False):
    item_doc = dao.get(tiid)
    if not item_doc:
        return None
    try:
        item = build_item_for_client(item_doc, myrefsets, dao, include_history)
    except Exception, e:
        item = None
        logger.error("Exception %s: Skipping item, unable to build %s, %s" % (e.__repr__(), tiid, str(item)))
    return item


def is_tiid_registered_to_anyone(tiid, mydao):
    res = mydao.view('registered_tiids/registered_tiids')    
    matches = res[[tiid]] 
    if matches.rows:
        #api_user_id = matches.rows[0]["id"]
        return True
    return False

def build_item_for_client(item, myrefsets, mydao, include_history=False):
    try:
        (genre, host) = decide_genre(item['aliases'])
        item["biblio"]['genre'] = genre
    except (KeyError, TypeError):
        logger.error("Skipping item, unable to lookup aliases or biblio in %s" % str(item))
        return None

    item["is_registered"] = is_tiid_registered_to_anyone(item["_id"], mydao)

    try:
        if "authors" in item["biblio"]:
            del item["biblio"]["authors_literal"]
    except (KeyError, TypeError):
        pass    

    metrics = item.setdefault("metrics", {})
    for metric_name in metrics:

        # Patch to hide Facebook data while we investigate potentially broken API.
        if "facebook" in metric_name.lower():
            continue

        #delete the raw history from what we return to the client for now
        if not include_history:
            try:
                del metrics[metric_name]["values"]["raw_history"]
            except KeyError:
                pass

        if metric_name in all_static_meta.keys():  # make sure we still support this metrics type
            # add static data

            metrics[metric_name]["static_meta"] = all_static_meta[metric_name]            

            # add normalization values
            # need year to calculate normalization below
            try:
                year = int(item["biblio"]["year"])
                if year < 2002:
                    year = 2002
                raw = metrics[metric_name]["values"]["raw"]
                normalized_values = get_normalized_values(genre, host, year, metric_name, raw, myrefsets)
                metrics[metric_name]["values"].update(normalized_values)
            except (KeyError, ValueError):
                logger.error("No good year in biblio for item {tiid}, no normalization".format(
                    tiid=item["_id"]))

    # ditch metrics we don't have static_meta for:
    item["metrics"] = {k:v for k, v in item["metrics"].iteritems() if "static_meta"  in v}

    return item

def add_metrics_data(metric_name, metrics_method_response, item):
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


def make():
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


def clean_for_export(item, supplied_key=None, secret_key=None):
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
        if "citeulike:" in metric_name:
            del cleaned_item["metrics"][metric_name]
    return cleaned_item


def decide_genre(alias_dict):
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

    elif "biblio" in alias_dict:
        genre = "article"

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

def canonical_alias_tuple(alias):
    (namespace, nid) = alias
    namespace = namespace.lower()
    if namespace=="doi":
        nid = nid.lower()
    return(namespace, nid)

def canonical_aliases(orig_aliases_dict):
    # only put lowercase namespaces in items, and lowercase dois
    lowercase_aliases_dict = {}
    for orig_namespace in orig_aliases_dict:
        lowercase_namespace = orig_namespace.lower()
        if lowercase_namespace == "doi":
            lowercase_aliases_dict[lowercase_namespace] = [doi.lower() for doi in orig_aliases_dict[orig_namespace]]
        else:
            lowercase_aliases_dict[lowercase_namespace] = orig_aliases_dict[orig_namespace]
    return lowercase_aliases_dict

def alias_tuples_from_dict(aliases_dict):
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

def alias_dict_from_tuples(aliases_tuples):
    alias_dict = {}
    for (ns, ids) in aliases_tuples:
        if ns in alias_dict:
            alias_dict[ns] += [ids]
        else:
            alias_dict[ns] = [ids]
    return alias_dict

def merge_alias_dicts(aliases1, aliases2):
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

def get_metric_names(providers_config):
    full_metric_names = []
    providers = ProviderFactory.get_providers(providers_config)
    for provider in providers:
        metric_names = provider.metric_names()
        for metric_name in metric_names:
            full_metric_names.append(provider.provider_name + ':' + metric_name)
    return full_metric_names

def get_normalized_values(genre, host, year, metric_name, value, myrefsets):
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
        # for nonarticles, use only the reference set type whose name matches the host (figshare, dryad, etc)
        if (genre != "article"):
            if (host != refsetname):
                continue  # skip this refset
        try:
            int_year = int(year)  #year is a number in the refset keys
            fencepost_values = myrefsets[genre][refsetname][int_year][metric_name].keys()
            myclosest = largest_value_that_is_less_than_or_equal_to(value, fencepost_values)
            response[refsetname] = myrefsets[genre][refsetname][int_year][metric_name][myclosest]
        except KeyError:
            #logger.info("No good lookup in %s %s %s for %s" %(genre, refsetname, year, metric_name))
            pass
        except ValueError:
            logger.error("Exception: no good lookup in %s %s %s for %s" %(genre, refsetname, year, metric_name))
            logger.debug("Value error calculating percentiles for %s %s %s for %s=%s" %(genre, refsetname, year, metric_name, str(value)))
            logger.debug("fencepost = {fencepost_values}".format(
                fencepost_values=fencepost_values))
            pass
            
    return response

def retrieve_items(tiids, myrefsets, myredis, mydao):
    something_currently_updating = False
    items = []
    for tiid in tiids:
        try:
            item = get_item(tiid, myrefsets, mydao)
        except (LookupError, AttributeError), e:
            logger.warning("Got an error looking up tiid '{tiid}'; error: {error}".format(
                    tiid=tiid, error=e.__repr__()))
            raise

        if not item:
            logger.warning("Looks like there's no item with tiid '{tiid}': ".format(
                    tiid=tiid))
            raise LookupError
            
        item["currently_updating"] = is_currently_updating(tiid, myredis)
        something_currently_updating = something_currently_updating or item["currently_updating"]

        items.append(item)
    return (items, something_currently_updating)

def is_currently_updating(tiid, myredis):
    num_providers_left = myredis.get_num_providers_left(tiid)
    if num_providers_left:
        currently_updating = myredis.get_num_providers_left(tiid) > 0
    else: # not in redis, maybe because it expired.  Assume it is not currently updating.
        currently_updating = False        
    return currently_updating

def create_or_update_items_from_aliases(aliases, myredis, mydao):
    logger.info("got a list of aliases; creating new items for them.")
    try:
        # remove unprintable characters and change list to tuples
        clean_aliases = [(clean_id(namespace), clean_id(nid)) for [namespace, nid] in aliases]
    except ValueError:
        logger.error("bad input to POST /collection (requires [namespace, id] pairs):{input}".format(
                input=str(aliases)
            ))
        return None

    logger.debug("POST /collection got list of aliases; create or find items for {aliases}".format(
            aliases=str(clean_aliases)
        ))

    (tiids, new_items) = create_or_find_items_from_aliases(clean_aliases, myredis, mydao)

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

    return (tiids, new_items)

def create_item(namespace, nid, myredis, mydao):
    logger.debug("In create_item with alias" + str((namespace, nid)))
    item = make()
    namespace = clean_id(namespace)
    nid = clean_id(nid)
    item["aliases"][namespace] = [nid]
    item["aliases"] = canonical_aliases(item["aliases"])

    # set this so we know when it's still updating later on
    myredis.set_num_providers_left(
        item["_id"],
        ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)
    )

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

def create_or_find_items_from_aliases(clean_aliases, myredis, mydao):
    tiids = []
    new_items = []
    for alias in clean_aliases:
        (namespace, nid) = alias
        existing_tiid = get_tiid_by_alias(namespace, nid, mydao)
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
            item = make()
            namespace = clean_id(namespace)
            nid = clean_id(nid)
            item["aliases"][namespace] = [nid]
            item["aliases"] = canonical_aliases(item["aliases"])

            new_items.append(item)
            tiids.append(item["_id"]) 

    # could be duplicate tiids if two aliases were synonymns. Return list of uniques
    unique_tiids = list(set(tiids))
    return(unique_tiids, new_items)

def create_item_from_namespace_nid(namespace, nid, myredis, mydao):
    # remove unprintable characters
    namespace = clean_id(namespace)
    nid = clean_id(nid)

    tiid = get_tiid_by_alias(namespace, nid, mydao)
    if tiid:
        logger.debug("... found with tiid " + tiid)
    else:
        tiid = create_item(namespace, nid, myredis, mydao)
        logger.debug("new item created with tiid " + tiid)

    return tiid

def get_tiid_by_alias(ns, nid, mydao):
    # clean before logging or anything
    ns = clean_id(ns)
    nid = clean_id(nid)

    res = mydao.view('queues/by_alias')

    # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults# for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
    logger.debug("In get_tiid_by_alias with {ns}, {nid}".format(
        ns=ns, nid=nid))

    # change input to lowercase etc
    (ns, nid) = canonical_alias_tuple((ns, nid))
    matches = res[[ns, nid]] 

    if matches.rows:
        if len(matches.rows) > 1:
            logger.warning("More than one tiid for alias (%s, %s)" % (ns, nid))
        tiid = matches.rows[0]["id"]
        logger.debug("found a match for {nid}!".format(nid=nid))
    else:
        logger.debug("no match for {nid}!".format(nid=nid))
        tiid = None
    return tiid

def start_item_update(tiids, myredis, mydao, sleep_in_seconds=0):
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


