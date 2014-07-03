from werkzeug import generate_password_hash, check_password_hash
import shortuuid, string, random, datetime
import csv, StringIO, json, copy
from collections import OrderedDict, defaultdict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.ext.hybrid import hybrid_property
from celery.result import AsyncResult

from totalimpact import db
from totalimpact import item as item_module
from totalimpact.item import Alias, Item
from totalimpact import json_sqlalchemy
from totalimpact.providers.provider import ProviderFactory

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.collection')

# print out extra debugging
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

def get_alias_strings(aliases):
    alias_strings = []
    for alias in aliases:
        alias = item_module.canonical_alias_tuple(alias)
        (namespace, nid) = alias
        try:
            alias_strings += [namespace+":"+nid]
        except TypeError:
            # jsonify the biblio dicts
            alias_strings += [namespace+":"+json.dumps(nid)]
    return alias_strings   

def add_items_to_collection_object(cid, tiids, alias_tuples=[]):
    # logger.debug(u"in add_items_to_collection_object for {cid}".format(
    #     cid=cid))        

    collection_obj = Collection.query.filter_by(cid=cid).first()
    if not collection_obj:
        return None
    collection_obj.last_modified = datetime.datetime.utcnow()
    db.session.merge(collection_obj)

    for tiid in tiids:
        if tiid not in collection_obj.tiids:
            collection_obj.tiid_links += [CollectionTiid(tiid=tiid)]

    # for alias_tuple in alias_tuples:
    #     try:
    #         alias_tuple = item_module.canonical_alias_tuple(alias_tuple)
    #         #logger.info(u"added_aliases: {added_aliases}, this tuple: {alias_tuple}".format(
    #         #    added_aliases=collection_obj.added_aliases, 
    #         #    alias_tuple=alias_tuple))
    #         if alias_tuple not in collection_obj.added_aliases:
    #             collection_obj.added_items += [AddedItem(alias_tuple=alias_tuple)]
    #     except ValueError:
    #         logger.debug("could not separate alias tuple {alias_tuple}".format(
    #             alias_tuple=alias_tuple))            

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_items_to_collection_object for {cid}, rolling back.  Message: {message}".format(
            cid=cid, 
            message=e.message)) 

    return collection_obj



def add_items_to_collection(cid, aliases, analytics_credentials, myredis, mydao=None):
    # logger.debug(u"in add_items_to_collection for {cid}".format(
    #     cid=cid))        

    tiids_aliases_map = item_module.create_tiids_from_aliases(aliases, analytics_credentials, myredis)

    # logger.debug(u"in add_items_to_collection with {tiids_aliases_map}".format(
    #     tiids_aliases_map=tiids_aliases_map)) 

    tiids = tiids_aliases_map.keys()
    aliases = tiids_aliases_map.values()

    collection_obj = add_items_to_collection_object(cid, tiids, aliases)

    return collection_obj


def remove_items_from_collection(cid, tiids_to_delete, myredis, mydao=None):
    # logger.debug(u"in remove_items_from_collection_object for {cid}".format(
    #     cid=cid))        

    collection_obj = Collection.query.filter_by(cid=cid).first()
    if not collection_obj:
        return None    
    collection_obj.last_modified = datetime.datetime.utcnow()
    db.session.merge(collection_obj)

    for coll_tiid in collection_obj.tiid_links:
        if coll_tiid.tiid in tiids_to_delete:
            collection_obj.tiid_links.remove(coll_tiid)

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in remove_items_from_collection_object for {cid}, rolling back.  Message: {message}".format(
            cid=cid, 
            message=e.message))

    return collection_obj


def create_new_collection_from_tiids(cid, title, tiids, ip_address, refset_metadata):
    # logger.debug(u"in create_new_collection_from_tiids for {cid}".format(
    #     cid=cid))        

    coll_doc, key = make(cid)
    if refset_metadata:
        coll_doc["refset_metadata"] = refset_metadata
    coll_doc["ip_address"] = ip_address
    coll_doc["title"] = title
    coll_doc["alias_tiids"] = dict(zip(tiids, tiids))

    collection_obj = create_objects_from_collection_doc(coll_doc)

    # logger.info(u"saved new collection '{id}' with {num_items} items.".format(
    #         id=coll_doc["_id"],
    #         num_items=len(coll_doc["alias_tiids"])))

    # logger.debug(json.dumps(coll_doc, sort_keys=True, indent=4))

    return (coll_doc, collection_obj)



def create_new_collection(cid, title, aliases, ip_address, refset_metadata, myredis, mydao):
    # logger.debug(u"in create_new_collection for {cid}".format(
    #     cid=cid))        

    analytics_credentials = {}
    tiids_aliases_map = item_module.create_tiids_from_aliases(aliases, analytics_credentials, myredis)

    # logger.debug(u"in add_items_to_collection with {tiids_aliases_map}".format(
    #     tiids_aliases_map=tiids_aliases_map)) 

    tiids = tiids_aliases_map.keys()
    aliases = tiids_aliases_map.values()

    coll_doc, key = make(cid)
    if refset_metadata:
        coll_doc["refset_metadata"] = refset_metadata
    coll_doc["ip_address"] = ip_address
    coll_doc["title"] = title
    alias_strings = get_alias_strings(aliases)
    coll_doc["alias_tiids"] = dict(zip(alias_strings, tiids))

    collection_obj = create_objects_from_collection_doc(coll_doc)

    # logger.info(u"saved new collection '{id}' with {num_items} items.".format(
    #         id=coll_doc["_id"],
    #         num_items=len(coll_doc["alias_tiids"])))

    # logger.debug(json.dumps(coll_doc, sort_keys=True, indent=4))

    return (coll_doc, collection_obj)


def create_objects_from_collection_doc(coll_doc):
    cid = coll_doc["_id"]
    
    # logger.debug(u"in create_objects_from_collection_doc for {cid}".format(
    #     cid=coll_doc["_id"]))        

    new_coll_object = Collection.query.filter_by(cid=coll_doc["_id"]).first()
    if not new_coll_object:
        new_coll_object = Collection.create_from_old_doc(coll_doc)
    db.session.add(new_coll_object)    

    tiids = coll_doc["alias_tiids"].values()
    for tiid in tiids:
        if tiid not in new_coll_object.tiids:
            new_coll_object.tiid_links += [CollectionTiid(tiid=tiid)]      

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in create_objects_from_collection_doc for {cid}, rolling back.  Message: {message}".format(
            cid=cid, 
            message=e.message))        

    return(new_coll_object)


def delete_collection(cid):
    coll_object = Collection.query.filter_by(cid=cid).first()
    db.session.delete(coll_object)
    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in delete_collection for {cid}, rolling back.  Message: {message}".format(
            cid=cid, 
            message=e.message))        
    return



class CollectionTiid(db.Model):
    cid = db.Column(db.Text, db.ForeignKey('collection.cid'), primary_key=True, index=True)
    tiid = db.Column(db.Text, primary_key=True)

    def __init__(self, **kwargs):
        logger.debug(u"new CollectionTiid {kwargs}".format(
            kwargs=kwargs))                
        super(CollectionTiid, self).__init__(**kwargs)

    def __repr__(self):
        return '<CollectionTiid {collection} {tiid}>'.format(
            collection=self.collection, 
            tiid=self.tiid)


class Collection(db.Model):
    cid = db.Column(db.Text, primary_key=True)
    created = db.Column(db.DateTime())
    last_modified = db.Column(db.DateTime())
    ip_address = db.Column(db.Text)
    title = db.Column(db.Text)
    refset_metadata = db.Column(json_sqlalchemy.JSONAlchemy(db.Text))
    tiid_links = db.relationship('CollectionTiid', lazy='subquery', cascade="all, delete-orphan",
        backref=db.backref("collection", lazy="subquery"))

    def __init__(self, collection_id=None, **kwargs):
        logger.debug(u"new Collection {kwargs}".format(
            kwargs=kwargs))                

        if collection_id is None:
            collection_id = _make_id()
        self.cid = collection_id

        now = datetime.datetime.utcnow()
        if "created" in kwargs:
            self.created = kwargs["created"]
        else:   
            self.created = now

        if "last_modified" in kwargs:
            self.last_modified = kwargs["last_modified"]
        else:   
            self.last_modified = now

        super(Collection, self).__init__(**kwargs)

    @property
    def tiids(self):
        return [tiid_link.tiid for tiid_link in self.tiid_links]

    # @property
    # def added_aliases(self):
    #     return [added_item.alias_tuple for added_item in self.added_items]

    def __repr__(self):
        return '<Collection {cid}, {title}>'.format(
            cid=self.cid, 
            title=self.title)


    @classmethod
    def create_from_old_doc(cls, doc):
        doc_copy = copy.deepcopy(doc)
        doc_copy["cid"] = doc_copy["_id"]
        for key in doc_copy.keys():
            if key not in ["cid", "created", "last_modified", "ip_address", "title", "refset_metadata"]:
                del doc_copy[key]
        new_collection_object = Collection(**doc_copy)
        return new_collection_object




#delete when we move to postgres
def make(collection_id=None):
    shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')
    key = shortuuid.uuid()[0:10]

    if collection_id is None:
        collection_id = _make_id()

    now = datetime.datetime.utcnow().isoformat()
    collection = {}

    collection["_id"] = collection_id
    collection["created"] = now
    collection["last_modified"] = now
    collection["type"] = "collection"
    collection["owner"] = None
    collection["key"] = key  # using the hash was needless complexity...

    return collection, key


def _make_id(len=6):
    '''Make an id string.

    Currently uses only lowercase and digits for better say-ability. Six
    places gives us around 2B possible values.
    '''
    choices = string.ascii_lowercase + string.digits
    return ''.join(random.choice(choices) for x in range(len))

def get_titles(cids, mydao=None):
    ret = {}
    for cid in cids:
        coll = Collection.query.filter_by(cid=cid).first()
        ret[cid] = coll.title
    return ret


def get_collection_doc_from_object(collection_obj):
    collection_doc = {}

    collection_doc["_id"] = collection_obj.cid
    collection_doc["type"] = "collection"
    collection_doc["title"] = collection_obj.title
    collection_doc["created"] = collection_obj.created.isoformat()
    collection_doc["last_modified"] = collection_obj.last_modified.isoformat()
    # don't include ip_address in info for client
    collection_doc["alias_tiids"] = {}
    tiids = collection_obj.tiids
    for tiid in tiids:
        collection_doc["alias_tiids"][tiid] = tiid  

    return(collection_doc)

def get_collection_doc(cid):
    collection_obj = Collection.query.get(cid)
    if not collection_obj:
        return None
    return get_collection_doc_from_object(collection_obj)


def is_all_done(tiids, myredis):
    statuses = [item_module.refresh_status(tiid, myredis) for tiid in tiids]
    all_done = all([refresh_status["short"].startswith(u"SUCCESS") for status in statuses])
    return all_done


def get_items_for_client(tiids, myrefsets, myredis, most_recent_metric_date=None, most_recent_diff_metric_date=None):
    item_metric_dicts = get_readonly_item_metric_dicts(tiids, most_recent_metric_date, most_recent_diff_metric_date)

    dict_of_item_docs = {}
    for tiid in item_metric_dicts:
        try:
            item_doc_for_client = item_module.build_item_for_client(item_metric_dicts[tiid], myrefsets, myredis)
            dict_of_item_docs[tiid] = item_doc_for_client
        except (KeyError, TypeError, AttributeError):
            logger.info(u"Couldn't build item {tiid}".format(tiid=tiid))
            raise
    
    return dict_of_item_docs

def get_most_recent_metrics(tiids, most_recent_metric_date=None):
    # we use string concatination below because haven't figured out bind params yet
    # abort if anything suspicious in tiids
    for tiid in tiids:
        for e in tiid:
            if not e.isalnum():
                return {}

    if not most_recent_metric_date:
        most_recent_metric_date = datetime.datetime.utcnow().isoformat()

    tiid_string = ",".join(["'"+tiid+"'" for tiid in tiids])    
    metric_objects = item_module.Snap.query.from_statement("""
        WITH max_collect AS 
            (SELECT tiid, provider, interaction, max(last_collected_date) AS last_collected_date
                FROM snap
                WHERE tiid in ({tiid_string})
                AND last_collected_date <= '{most_recent_metric_date}'::date + 1               
                GROUP BY tiid, provider, interaction
                ORDER by tiid, provider)
            SELECT max_collect.*, m.raw_value, m.drilldown_url, m.snap_id
                FROM snap m
                NATURAL JOIN max_collect""".format(
                    tiid_string=tiid_string, most_recent_metric_date=most_recent_metric_date)).all()

    # logger.debug("*** get_previous_metrics {most_recent_metric_date} metric_objects = {metric_objects}".format(
    #     most_recent_metric_date=most_recent_metric_date, metric_objects=metric_objects))

    return metric_objects


def get_previous_metrics(tiids, most_recent_diff_metric_date=None):
    # we use string concatination below because haven't figured out bind params yet
    # abort if anything suspicious in tiids
    for tiid in tiids:
        for e in tiid:
            if not e.isalnum():
                return {}

    if not most_recent_diff_metric_date:
        most_recent_diff_metric_date = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()

    tiid_string = ",".join(["'"+tiid+"'" for tiid in tiids])    
    metric_objects = item_module.Snap.query.from_statement("""
        WITH max_collect AS 
            (SELECT tiid, provider, interaction, max(last_collected_date) AS last_collected_date
                FROM snap
                WHERE tiid in ({tiid_string})
                AND last_collected_date <= '{most_recent_diff_metric_date}'::date
                GROUP BY tiid, provider, interaction
                ORDER by tiid, provider)
        SELECT max_collect.*, m.raw_value, m.drilldown_url, m.snap_id
            FROM snap m
            NATURAL JOIN max_collect""".format(
                tiid_string=tiid_string, most_recent_diff_metric_date=most_recent_diff_metric_date)).all()

    # logger.debug("*** get_previous_metrics {most_recent_diff_metric_date} metric_objects = {metric_objects}".format(
    #     most_recent_diff_metric_date=most_recent_diff_metric_date, metric_objects=metric_objects))

    return metric_objects


def get_readonly_item_metric_dicts(tiids, most_recent_metric_date=None, most_recent_diff_metric_date=None):
    # logger.info(u"in get_readonly_item_metric_dicts")

    item_objects = Item.query.filter(Item.tiid.in_(tiids)).all()
    items_by_tiid = {}
    metrics_summaries = {}
    for item_obj in item_objects:
        items_by_tiid[item_obj.tiid] = {
            "item_obj": item_obj, 
            "metrics_summaries": defaultdict(dict)}

    db.session.expunge_all()

    metric_objects_recent = get_most_recent_metrics(tiids, most_recent_metric_date)
    for metric_object in metric_objects_recent:
        items_by_tiid[metric_object.tiid]["metrics_summaries"][metric_object.fully_qualified_name]["most_recent"] = copy.copy(metric_object)

    metric_objects_7_days_ago = get_previous_metrics(tiids, most_recent_diff_metric_date)
    for metric_object in metric_objects_7_days_ago:
        items_by_tiid[metric_object.tiid]["metrics_summaries"][metric_object.fully_qualified_name]["7_days_ago"] = copy.copy(metric_object)

    return items_by_tiid


def get_collection_with_items_for_client(cid, myrefsets, myredis, mydao, include_history=False):
    collection_obj = Collection.query.get(cid)
    collection_doc = get_collection_doc_from_object(collection_obj)
    if not collection_doc:
        return (None, None)

    collection_doc["items"] = []
    tiids = collection_obj.tiids

    if tiids:
        item_metric_dicts = get_readonly_item_metric_dicts(tiids)

        for tiid in item_metric_dicts:
            #logger.info(u"got item {tiid} for {cid}".format(
            #    tiid=item_obj.tiid, cid=cid))
            try:
                item_for_client = item_module.build_item_for_client(item_metric_dicts[tiid], myrefsets, myredis)
            except (KeyError, TypeError, AttributeError):
                logger.info(u"Couldn't build item {tiid}, excluding it from the returned collection {cid}".format(
                    tiid=tiid, cid=cid))
                item_for_client = None
                raise
            if item_for_client:
                collection_doc["items"] += [item_for_client]
    
    something_currently_updating = not is_all_done(tiids, myredis)

    # logger.debug(u"Got items for collection_doc %s" %cid)

    return (collection_doc, something_currently_updating)

def clean_value_for_csv(value_to_store):
    try:
        value_to_store = value_to_store.encode("utf-8").strip()
    except AttributeError:
        pass
    return value_to_store

def make_csv_rows(items):
    header_metric_names = []
    for item in items:
        header_metric_names += item["metrics"].keys()
    header_metric_names = sorted(list(set(header_metric_names)))

    header_alias_names = ["title", "doi"]

    # make header row
    header_list = ["tiid"] + header_alias_names + header_metric_names
    ordered_fieldnames = OrderedDict([(col, None) for col in header_list])

    # body rows
    rows = []
    for item in items:
        ordered_fieldnames = OrderedDict()
        ordered_fieldnames["tiid"] = item["_id"]
        for alias_name in header_alias_names:
            try:
                if alias_name=="title":
                    ordered_fieldnames[alias_name] = clean_value_for_csv(item['aliases']['biblio'][0]['title'])
                else:
                    ordered_fieldnames[alias_name] = clean_value_for_csv(item['aliases'][alias_name][0])
            except (AttributeError, KeyError):
                ordered_fieldnames[alias_name] = ""
        for metric_name in header_metric_names:
            try:
                raw_value = item['metrics'][metric_name]['values']['raw']
                ordered_fieldnames[metric_name] = clean_value_for_csv(raw_value)
            except (AttributeError, KeyError):
                ordered_fieldnames[metric_name] = ""
        rows += [ordered_fieldnames]
    return(ordered_fieldnames, rows)

def make_csv_stream(items):
    (header, rows) = make_csv_rows(items)

    mystream = StringIO.StringIO()
    dw = csv.DictWriter(mystream, delimiter=',', dialect=csv.excel, fieldnames=header)
    dw.writeheader()
    for row in rows:
        dw.writerow(row)
    contents = mystream.getvalue()
    mystream.close()
    return contents

def get_metric_value_lists(items):
    (ordered_fieldnames, rows) = make_csv_rows(items)
    metric_values = {}
    for metric_name in ProviderFactory.get_all_metric_names():
        if metric_name in ordered_fieldnames:
            if metric_name in ["tiid", "title", "doi"]:
                pass
            else:
                values = [row[metric_name] for row in rows]
                values = [value if value else 0 for value in values]
                # treat "Yes" as 1 for normalizaations
                values = [1 if value=="Yes" else value for value in values]
                metric_values[metric_name] = sorted(values, reverse=True)
        else:
            metric_values[metric_name] = [0 for row in rows]
    return metric_values

def get_metric_values_of_reference_sets(items):
    metric_value_lists = get_metric_value_lists(items)
    metrics_to_normalize = metric_value_lists.keys()
    for key in metrics_to_normalize:
        if ("plosalm" in key):
            del metric_value_lists[key]
        elif not isinstance(metric_value_lists[key][0], (int, float)):
            del metric_value_lists[key]
    return metric_value_lists  

def get_normalization_confidence_interval_ranges(metric_value_lists, confidence_interval_table):
    matches = {}
    response = {}
    for metric_name in metric_value_lists:
        metric_values = sorted(metric_value_lists[metric_name], reverse=False)
        if (len(confidence_interval_table) != len(metric_values)):
            logger.error(u"Was expecting normalization set to be {expected_len} but it is {actual_len}. Not loading.".format(
                expected_len=len(confidence_interval_table), actual_len=len(metric_values) ))
        matches[metric_name] = defaultdict(list)
        num_normalization_points = len(metric_values)
        for i in range(num_normalization_points):
            matches[metric_name][metric_values[i]] += [[(i*100)/num_normalization_points, confidence_interval_table[i][0], confidence_interval_table[i][1]]]

        response[metric_name] = {}
        for metric_value in matches[metric_name]:
            lowers = [lower for (est, lower, upper) in matches[metric_name][metric_value]]
            uppers = [upper for (est, lower, upper) in matches[metric_name][metric_value]]

            estimates = [est for (est, lower, upper) in matches[metric_name][metric_value]]

            response[metric_name][metric_value] = {
                "CI95_lower": min(lowers),
                "CI95_upper": max(uppers),
                "estimate_upper":  max(estimates),
                "estimate_lower": min(estimates)
                }

            # If ties, check and see if next higher metric value already has an estimate.
            # If not, assign it the estimate of the top range of the tied values, so 
            # that the metric_value+1 isn't conservatively assigned percentiles for the 
            # tie of the value below it
            if len(lowers) > 1:
                if not (metric_value+1 in response[metric_name]):
                    response[metric_name][metric_value+1] = {
                        "CI95_lower": max(lowers),
                        "CI95_upper": max(uppers),
                        "estimate_upper":  max(estimates),
                        "estimate_lower": max(estimates)
                        }


        # add a value that is one larger than the biggest value, hack the lower 95 bound to be a bit higher
        # than the 99th percentile
        largest_metric_value = max(matches[metric_name].keys())
        onehundredth_percentile_value = largest_metric_value + 1
        final_entry_in_conf_table = confidence_interval_table[-1]
        final_entry_CI95_lower = final_entry_in_conf_table[0]
        response[metric_name][onehundredth_percentile_value] = {
                "CI95_lower": final_entry_CI95_lower+1,
                "CI95_upper": 100,
                "estimate_upper": 100,
                "estimate_lower": 100
                }

    return response


def build_all_reference_lookups(myredis, mydao):
    # for expediency, assuming all reference collections are this size
    # risky assumption, but run with it for now!
    size_of_reference_collections = 100
    confidence_interval_level = 0.95
    percentiles = range(100)

    confidence_interval_table = myredis.get_confidence_interval_table(size_of_reference_collections, confidence_interval_level)
    if not confidence_interval_table:
        table_return = calc_confidence_interval_table(size_of_reference_collections, 
                confidence_interval_level=confidence_interval_level, 
                percentiles=percentiles)
        confidence_interval_table = table_return["lookup_table"]
        myredis.set_confidence_interval_table(size_of_reference_collections, 
                                                confidence_interval_level, 
                                                confidence_interval_table)        
        #print(json.dumps(confidence_interval_table, indent=4))

    # logger.info(u"querying for reference_set_rows")

    reference_set_rows = Collection.query.filter(Collection.refset_metadata != None).all()

    #res = mydao.db.view("reference-sets/reference-sets", descending=True, include_docs=False, limits=100)
    #logger.info(u"Number rows = " + str(len(res.rows)))
    reference_lookup_dict = {"article": defaultdict(dict), "dataset": defaultdict(dict), "software": defaultdict(dict)}
    reference_histogram_dict = {"article": defaultdict(dict), "dataset": defaultdict(dict), "software": defaultdict(dict)}

    # randomize rows so that multiple gunicorn instances hit them in different orders
    randomized_rows = reference_set_rows
    random.shuffle(randomized_rows)
    if randomized_rows:
        for row in randomized_rows:
            try:
                #(cid, title) = row.key
                #refset_metadata = row.value
                cid = row.cid
                title = row.title
                refset_metadata = row.refset_metadata
                genre = refset_metadata["genre"]
                year = refset_metadata["year"]
                refset_name = refset_metadata["name"]
                refset_version = refset_metadata["version"]
                if refset_version < 0.1:
                    logger.error(u"Refset version too low for '%s', not loading its normalizations" %str(row.key))
                    continue
            except ValueError:
                logger.error(u"Normalization '%s' not formatted as expected, not loading its normalizations" %str(row.key))
                continue

            histogram = myredis.get_reference_histogram_dict(genre, refset_name, year)
            lookup = myredis.get_reference_lookup_dict(genre, refset_name, year)
            
            if histogram and lookup:
                logger.info(u"Loaded successfully from cache")
                reference_histogram_dict[genre][refset_name][year] = histogram
                reference_lookup_dict[genre][refset_name][year] = lookup
            else:
                logger.info(u"Not found in cache, so now building from items")
                if refset_name:
                    try:
                        # send it without reference sets because we are trying to load the reference sets here!
                        (coll_with_items, is_updating) = get_collection_with_items_for_client(cid, None, myredis, mydao)
                    except (LookupError, AttributeError):       
                        raise #not found

                    logger.info(u"Loading normalizations for %s" %coll_with_items["title"])

                    # hack for now to get big collections
                    normalization_numbers = get_metric_values_of_reference_sets(coll_with_items["items"])
                    reference_histogram_dict[genre][refset_name][year] = normalization_numbers

                    reference_lookup = get_normalization_confidence_interval_ranges(normalization_numbers, confidence_interval_table)
                    reference_lookup_dict[genre][refset_name][year] = reference_lookup

                    # save to redis
                    myredis.set_reference_histogram_dict(genre, refset_name, year, normalization_numbers)
                    myredis.set_reference_lookup_dict(genre, refset_name, year, reference_lookup)

    return(reference_lookup_dict, reference_histogram_dict)

# from http://userpages.umbc.edu/~rcampbel/Computers/Python/probstat.html
# also called binomial coefficient
def choose(n, k):
   accum = 1
   for m in range(1,k+1):
      accum = accum*(n-k+m)/m
   return accum

# from formula at http://www.milefoot.com/math/stat/ci-medians.htm
def probPercentile(p, n, i):
    prob = choose(n, i) * p**i * (1-p)**(n-i)
    return(prob)

def calc_confidence_interval_table(
        n,                              # sample size
        confidence_interval_level=0.95, # confidence interval threshold
        percentiles=range(8, 97, 2) # percentiles to calculate.  Median==50.
        ):
    percentile_lower_bound = [None for i in range(n)]
    percentile_upper_bound = [None for i in range(n)]
    limits = {}
    range_sum = {}
    for percentile in percentiles:
        #print(percentile)
        order_statistic_probs = {}
        for i in range(0, n+1):
            order_statistic_probs[i] = probPercentile(percentile*0.01, n, i)
        #print(order_statistic_probs)
        max_order_statistic_prob = [(i, order_statistic_probs[i]) 
            for i in order_statistic_probs 
                if order_statistic_probs[i]==max(order_statistic_probs.values())]
        lower_max_order_statistic_prob = min([i for (i, val) in max_order_statistic_prob])
        upper_max_order_statistic_prob = max([i for (i, val) in max_order_statistic_prob])
        for i in range(0, n/2):
            myrange = range(max(0, (lower_max_order_statistic_prob-i)), 
                            min(len(order_statistic_probs), (1+upper_max_order_statistic_prob+i)))
            range_sum[percentile] = sum([order_statistic_probs[j] for j in myrange])
            if range_sum[percentile] >= confidence_interval_level:
                #print range_sum[percentile]
                limits[percentile] = (min(myrange), 1+max(myrange))
                #print "from index %i to (but not including) %i" %(limits[percentile][0], limits[percentile][1])
                for i in myrange[0:-1]:
                    percentile_upper_bound[i] = percentile
                    if not percentile_lower_bound[i]:
                        percentile_lower_bound[i] = percentile
                break

    #for i in range(n-1, 0, -1):
    #    print (i+0.0)/n, ps_min[i], ps_max[i]
    return({"range_sum":range_sum, 
            "limits":limits, 
            "lookup_table":zip(percentile_lower_bound, percentile_upper_bound)})






