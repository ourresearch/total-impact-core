from werkzeug import generate_password_hash, check_password_hash
import shortuuid, datetime, hashlib, threading, json, time, copy, re

from totalimpact.providers.provider import ProviderFactory
from totalimpact.providers.provider import ProviderTimeout, ProviderServerError
from totalimpact import unicode_helpers

from totalimpact import default_settings
from totalimpact.utils import Retry

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.sql import text    

from totalimpact import json_sqlalchemy, tiredis
from totalimpact import db


# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.item')

# print out extra debugging
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


all_static_meta = ProviderFactory.get_all_static_meta()



class NotAuthenticatedError(Exception):
    pass

def delete_item(tiid):
    item_object = Item.from_tiid(tiid)
    db.session.delete(item_object)
    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in delete_item for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message))   


def create_metric_objects(old_style_metric_dict):
    new_metric_objects = []

    for full_metric_name in old_style_metric_dict:
        (provider, metric_name) = full_metric_name.split(":")
        metric_details = old_style_metric_dict[full_metric_name]
        new_style_metric_dict = {
            "metric_name": metric_name, 
            "provider": provider, 
            "drilldown_url": metric_details["provenance_url"]
        }

        for collected_date in metric_details["values"]["raw_history"]:
            new_style_metric_dict["collected_date"] = collected_date
            new_style_metric_dict["raw_value"] = metric_details["values"]["raw_history"][collected_date]
            metric_object = Metric(**new_style_metric_dict)
            new_metric_objects += [metric_object]    

    return new_metric_objects


def create_biblio_objects(list_of_old_style_biblio_dicts, collected_date=datetime.datetime.utcnow()):
    new_biblio_objects = []

    provider_number = 0
    for biblio_dict in list_of_old_style_biblio_dicts:
        provider_number += 1
        provider = "unknown" + str(provider_number)
        for biblio_name in biblio_dict:
            biblio_object = Biblio(biblio_name=biblio_name, 
                    biblio_value=biblio_dict[biblio_name], 
                    provider=provider, 
                    collected_date=collected_date)
            new_biblio_objects += [biblio_object]

    return new_biblio_objects


def create_alias_objects(old_style_alias_dict, collected_date=datetime.datetime.utcnow()):
    new_alias_objects = []
    alias_tuples = alias_tuples_from_dict(old_style_alias_dict)   
    for alias_tuple in alias_tuples:
        (namespace, nid) = alias_tuple
        if nid and namespace and (namespace != "biblio"):
            new_alias_objects += [Alias(alias_tuple=alias_tuple, collected_date=collected_date)]
    return new_alias_objects


def create_objects_from_item_doc(item_doc, skip_if_exists=False):
    tiid = item_doc["_id"]

    logger.debug(u"in create_objects_from_item_doc for {tiid}".format(
        tiid=item_doc["_id"]))        

    new_item_object = Item.from_tiid(item_doc["_id"])
    if new_item_object and skip_if_exists:
        return new_item_object
    else:
        new_item_object = Item.create_from_old_doc(item_doc)
    db.session.add(new_item_object)

    alias_dict = item_doc["aliases"]
    new_alias_objects = create_alias_objects(alias_dict, item_doc["last_modified"])
    new_item_object.aliases = new_alias_objects

    # biblio within aliases, skip just the biblio section
    if "biblio" in alias_dict:
        new_biblio_objects = create_biblio_objects(alias_dict["biblio"], item_doc["last_modified"]) 
        new_item_object.biblios = new_biblio_objects

    new_metric_objects = None
    if "metrics" in item_doc:
        new_metric_objects = create_metric_objects(item_doc["metrics"]) 
        for metric in new_metric_objects:
            metric.tiid = item_doc["_id"]
            db.session.add(metric)

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in create_objects_from_item_doc for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message))   

    # have to set it because after the commit the metrics aren't set any more
    if new_metric_objects:
        new_item_object.metrics = new_metric_objects

    return new_item_object



class Metric(db.Model):
    tiid = db.Column(db.Text, db.ForeignKey('item.tiid'), primary_key=True, index=True)
    provider = db.Column(db.Text, primary_key=True)
    metric_name = db.Column(db.Text, primary_key=True)
    collected_date = db.Column(db.DateTime(), primary_key=True)
    raw_value = db.Column(json_sqlalchemy.JSONAlchemy(db.Text))
    drilldown_url = db.Column(db.Text)

    def __init__(self, **kwargs):
        if "collected_date" in kwargs:
            self.collected_date = kwargs["collected_date"]
        else:
            self.collected_date = datetime.datetime.utcnow()
        super(Metric, self).__init__(**kwargs)

    def __repr__(self):
        return '<Metric {tiid} {provider}:{metric_name}>'.format(
            provider=self.provider, 
            metric_name=self.metric_name, 
            tiid=self.tiid)


class Biblio(db.Model):
    tiid = db.Column(db.Text, db.ForeignKey('item.tiid'), primary_key=True, index=True)
    provider = db.Column(db.Text, primary_key=True)
    biblio_name = db.Column(db.Text, primary_key=True)
    biblio_value = db.Column(json_sqlalchemy.JSONAlchemy(db.Text))
    collected_date = db.Column(db.DateTime())

    def __init__(self, **kwargs):
        # logger.debug(u"new Biblio {kwargs}".format(
        #     kwargs=kwargs))                

        if "collected_date" in kwargs:
            self.collected_date = kwargs["collected_date"]
        else:   
            self.collected_date = datetime.datetime.utcnow()
        if not "provider" in kwargs:
            self.provider = "unknown"
           
        super(Biblio, self).__init__(**kwargs)

    def __repr__(self):
        return '<Biblio {biblio_name}, {item}>'.format(
            biblio_name=self.biblio_name, 
            item=self.item)

    @classmethod
    def filter_by_tiid(cls, tiid):
        response = cls.query.filter_by(tiid=tiid).all()
        return response

    @classmethod
    def as_dict_by_tiid(cls, tiid):
        response = {}
        biblio_elements = cls.query.filter_by(tiid=tiid).all()
        for biblio in biblio_elements:
            response[biblio.biblio_name] = biblio.biblio_value
        return response


class Alias(db.Model):
    tiid = db.Column(db.Text, db.ForeignKey('item.tiid'), primary_key=True, index=True)
    namespace = db.Column(db.Text, primary_key=True)
    nid = db.Column(db.Text, primary_key=True)
    collected_date = db.Column(db.DateTime())

    def __init__(self, **kwargs):
        # logger.debug(u"new Alias {kwargs}".format(
        #     kwargs=kwargs))                

        if "alias_tuple" in kwargs:
            alias_tuple = canonical_alias_tuple(kwargs["alias_tuple"])
            (namespace, nid) = alias_tuple
            self.namespace = namespace
            self.nid = nid                
        if "collected_date" in kwargs:
            self.collected_date = kwargs["collected_date"]
        else:   
            self.collected_date = datetime.datetime.utcnow()

        super(Alias, self).__init__(**kwargs)
        
    @hybrid_property
    def alias_tuple(self):
        return ((self.namespace, self.nid))

    @alias_tuple.setter
    def alias_tuple(self, alias_tuple):
        try:
            (namespace, nid) = alias_tuple
        except ValueError:
            logger.debug("could not separate alias tuple {alias_tuple}".format(
                alias_tuple=alias_tuple))
            raise
        self.namespace = namespace
        self.nid = nid        

    def __repr__(self):
        return '<Alias {item}, {alias_tuple}>'.format(
            item=self.item,
            alias_tuple=self.alias_tuple)

    @classmethod
    def filter_by_alias(cls, alias_tuple):
        alias_tuple = canonical_alias_tuple(alias_tuple)
        (namespace, nid) = alias_tuple
        response = cls.query.filter_by(namespace=namespace, nid=nid)
        return response


class Item(db.Model):
    tiid = db.Column(db.Text, primary_key=True)
    created = db.Column(db.DateTime())
    last_modified = db.Column(db.DateTime())
    last_update_run = db.Column(db.DateTime())
    aliases = db.relationship('Alias', lazy='subquery', cascade="all, delete-orphan",
        backref=db.backref("item", lazy="subquery"))
    biblios = db.relationship('Biblio', lazy='subquery', cascade="all, delete-orphan",
        backref=db.backref("item", lazy="subquery"))
    metrics = db.relationship('Metric', lazy='noload', cascade="all, delete-orphan",
        backref=db.backref("item", lazy="noload"))
    metrics_query = db.relationship('Metric', lazy='dynamic')

    def __init__(self, **kwargs):
        # logger.debug(u"new Item {kwargs}".format(
        #     kwargs=kwargs))                

        if "tiid" in kwargs:
            self.tiid = kwargs["tiid"]
        else:
            self.tiid = shortuuid.uuid()[0:24]
       
        now = datetime.datetime.utcnow()
        if "created" in kwargs:
            self.created = kwargs["created"]
        else:   
            self.created = now
        if "last_modified" in kwargs:
            self.last_modified = kwargs["last_modified"]
        else:   
            self.last_modified = now
        if "last_update_run" in kwargs:
            self.last_update_run = kwargs["last_update_run"]
        else:   
            self.last_update_run = now

        super(Item, self).__init__(**kwargs)

    def __repr__(self):
        return '<Item {tiid}>'.format(
            tiid=self.tiid)

    @classmethod
    def from_tiid(cls, tiid):
        item = cls.query.get(tiid)
        if not item:
            return None
        item.metrics = item.metrics_query.all()
        return item

    @property
    def alias_tuples(self):
        return [alias.alias_tuple for alias in self.aliases]

    @property
    def publication_date(self):
        publication_date = None
        for biblio in self.biblios:
            if biblio.biblio_name == "date":
                publication_date = biblio.biblio_value
                continue
            if (biblio.biblio_name == "year") and biblio.biblio_value:
                publication_date = datetime.datetime(int(biblio.biblio_value), 12, 31)

        if not publication_date:
            publication_date = self.created
        return publication_date.isoformat()

    @hybrid_method
    def published_before(self, mydate):
        return (self.publication_date < mydate.isoformat())

    @classmethod
    def create_from_old_doc(cls, doc):
        logger.debug(u"in create_from_old_doc for {tiid}".format(
            tiid=doc["_id"]))

        doc_copy = copy.deepcopy(doc)
        doc_copy["tiid"] = doc_copy["_id"]
        for key in doc_copy.keys():
            if key not in ["tiid", "created", "last_modified", "last_update_run"]:
                del doc_copy[key]
        new_item_object = Item(**doc_copy)

        return new_item_object

    def as_old_doc(self):
        # logger.debug(u"in as_old_doc for {tiid}".format(
        #     tiid=self.tiid))

        item_doc = {}
        item_doc["_id"] = self.tiid
        item_doc["last_modified"] = self.last_modified.isoformat()
        item_doc["created"] = self.created.isoformat()
        item_doc["type"] = "item"

        item_doc["biblio"] = {}
        for biblio in self.biblios:
            item_doc["biblio"][biblio.biblio_name] = biblio.biblio_value    

        item_doc["aliases"] = alias_dict_from_tuples(self.alias_tuples)
        if item_doc["biblio"]:
            item_doc["aliases"]["biblio"] = [item_doc["biblio"]]

        item_doc["metrics"] = {}
        for metric in self.metrics:
            metric_name = metric.provider + ":" + metric.metric_name
            metrics_method_response = (metric.raw_value, metric.drilldown_url)
            item_doc = add_metrics_data(metric_name, metrics_method_response, item_doc, metric.collected_date.isoformat())

        for full_metric_name in item_doc["metrics"]:
            most_recent_date_so_far = "1900"
            for this_date in item_doc["metrics"][full_metric_name]["values"]["raw_history"]:
                if this_date > most_recent_date_so_far:
                    most_recent_date_so_far = this_date
                    item_doc["metrics"][full_metric_name]["values"]["raw"] = item_doc["metrics"][full_metric_name]["values"]["raw_history"][this_date]

        return item_doc


def largest_value_that_is_less_than_or_equal_to(target, collection):
    collection_as_numbers = [(int(i), i) for i in collection if int(i) <= target]
    if collection_as_numbers:
        response = max(collection_as_numbers)[1]
    else:
        # the value is lower than anything we've seen before, so return lowest value
        response = min([(int(i), i) for i in collection])[1]
    return response


def clean_id(nid):
    try:
        nid = nid.strip(' "')
        nid = unicode_helpers.remove_nonprinting_characters(nid)
    except (TypeError, AttributeError):
        #isn't a string.  That's ok, might be biblio
        pass
    return(nid)

def get_item(tiid, myrefsets, myredis):
    item_obj = Item.from_tiid(tiid)

    item_doc = item_obj.as_old_doc()
    if not item_doc:
        return None
    try:
        item_for_client = build_item_for_client(item_doc, myrefsets, myredis)
    except Exception, e:
        item_for_client = None
        logger.error(u"Exception %s: Skipping item, unable to build %s, %s" % (e.__repr__(), tiid, str(item_for_client)))
    return item_for_client



def build_item_for_client(item, myrefsets, myredis):
    # logger.debug(u"in build_item_for_client {tiid}".format(
    #     tiid=item["_id"]))

    try:
        (genre, host) = decide_genre(item['aliases'])
        item["biblio"]['genre'] = genre
    except (KeyError, TypeError):
        logger.error(u"Skipping item, unable to lookup aliases or biblio in %s" % str(item))
        return None

    try:
        if "authors" in item["biblio"]:
            del item["biblio"]["authors_literal"]
    except (KeyError, TypeError):
        pass    

    metrics = item.setdefault("metrics", {})
    for metric_name in metrics:

        # logger.debug(u"in build_item_for_client, working on {metric_name}".format(
        #     metric_name=metric_name))

        #delete the raw history from what we return to the client for now
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
                #logger.error(u"No good year in biblio for item {tiid}, no normalization".format(
                #    tiid=item["_id"]))
                pass

    # ditch metrics we don't have static_meta for:
    item["metrics"] = {k:v for k, v in item["metrics"].iteritems() if "static_meta"  in v}

    item["currently_updating"] = is_currently_updating(item["_id"], myredis)

    return item

def as_int_or_float_if_possible(input_value):
    value = input_value
    try:
        value = int(input_value)
    except (ValueError, TypeError):
        try:
            value = float(input_value)
        except (ValueError, TypeError):
            pass
    return(value)


def add_metrics_data(metric_name, metrics_method_response, item, timestamp=None):
    metrics = item.setdefault("metrics", {})
    
    (metric_value, provenance_url) = metrics_method_response

    this_metric = metrics.setdefault(metric_name, {})
    this_metric["provenance_url"] = provenance_url

    this_metric_values = this_metric.setdefault("values", {})
    this_metric_values["raw"] = as_int_or_float_if_possible(metric_value)

    this_metric_values_raw_history = this_metric_values.setdefault("raw_history", {})
    if not timestamp:
        timestamp = datetime.datetime.utcnow().isoformat()
    this_metric_values_raw_history[timestamp] = as_int_or_float_if_possible(metric_value)
    return item


def add_metric_to_item_object(full_metric_name, metrics_method_response, item_doc):
    tiid = item_doc["_id"]
    # logger.debug(u"in add_metrics_to_item_object for {tiid}".format(
    #     tiid=tiid))

    (metric_value, provenance_url) = metrics_method_response
    (provider, metric_name) = full_metric_name.split(":")

    new_style_metric_dict = {
        "tiid": item_doc["_id"],
        "metric_name": metric_name, 
        "provider": provider, 
        "raw_value": metric_value,
        "drilldown_url": provenance_url,
        "collected_date": datetime.datetime.utcnow()
    }    
    metric_object = Metric(**new_style_metric_dict)
    db.session.add(metric_object)

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_metric_to_item_object for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 

    item_obj = Item.from_tiid(tiid)

    return item_obj


def add_aliases_to_item_object(aliases_dict, item_doc):
    tiid = item_doc["_id"]
    logger.debug(u"in add_aliases_to_item_object for {tiid}".format(
        tiid=tiid))        

    item_obj = Item.from_tiid(tiid)
    if not item_obj:
        item_obj = create_objects_from_item_doc(item_doc)

    item_obj.last_modified = datetime.datetime.utcnow()
    db.session.merge(item_obj)

    alias_objects = create_alias_objects(aliases_dict)
    for alias_obj in alias_objects:
        if not alias_obj.alias_tuple in item_obj.alias_tuples:
            item_obj.aliases.append(alias_obj)    

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_aliases_to_item_object for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 
    return item_obj

def add_biblio_to_item_object(new_biblio_dict, item_doc):
    tiid = item_doc["_id"]
    logger.debug(u"in add_biblio_to_item_object for {tiid}, /biblio_print {new_biblio_dict}".format(
        tiid=tiid, 
        new_biblio_dict=new_biblio_dict))        

    item_obj = Item.from_tiid(tiid)
    if not item_obj:
        item_obj = create_objects_from_item_doc(item_doc)
    item_obj.last_modified = datetime.datetime.utcnow()
    db.session.merge(item_obj)

    item_obj.biblios += create_biblio_objects([new_biblio_dict])

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_biblio_to_item_object for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 
        
    return item_obj



def get_biblio_to_update(old_biblio, new_biblio):
    response = None
    if old_biblio:
        try:
            if old_biblio["title"] == "AOP":
                response = new_biblio
        except KeyError:
            response = new_biblio
    else:
        response = new_biblio

    return response


def make():
    now = datetime.datetime.utcnow().isoformat()
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
    # logger.debug(u"in decide_genre with {alias_dict}".format(
    #     alias_dict=alias_dict))        

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
            host = "figshare"
            try:
                genre = alias_dict["biblio"][0]["genre"]
            except (KeyError, AttributeError):
                genre = "dataset"
        else:
            genre = "article"

    elif "pmid" in alias_dict:
        genre = "article"

    elif "blog" in alias_dict:
        genre = "blog"
        host = "wordpresscom"

    elif "blog_post" in alias_dict:
        genre = "blog"
        host = "blog_post"

    elif "url" in alias_dict:
        joined_url_string = "".join(alias_dict["url"])
        joined_url_string = joined_url_string.lower()
        if "slideshare.net" in joined_url_string:
            genre = "slides"
            host = "slideshare"
        elif "github.com" in joined_url_string:
            genre = "software"
            host = "github"
        elif "twitter.com" in joined_url_string:
            if "/status/" in joined_url_string:
                genre = "twitter"
                host = "twitter_tweet"
            else:
                genre = "twitter"
                host = "twitter_account"
        elif "youtube.com" in joined_url_string:
            genre = "video"
            host = "youtube"
        elif "vimeo.com" in joined_url_string:
            genre = "video"
            host = "vimeo"
        else:
            genre = "webpage"
            host = "webpage"

    # override if it came in with a genre, or call it an "article" if it has a journal
    if (host=="unknown" and ("biblio" in alias_dict)):
        for biblio_dict in alias_dict["biblio"]:
            if "genre" in biblio_dict and (biblio_dict["genre"] not in ["undefined", "other"]):
                if "article" in biblio_dict["genre"]:
                    genre = "article"  #disregard whether journal article or conference article for now
                else:
                    genre = biblio_dict["genre"]
            elif ("journal" in biblio_dict) and biblio_dict["journal"]:  
                genre = "article"

    return (genre, host)


def canonical_alias_tuple(alias):
    (namespace, nid) = alias
    namespace = clean_id(namespace)
    nid = clean_id(nid)
    namespace = namespace.lower()
    if namespace=="doi":
        nid = nid.lower()
    return(namespace, nid)

def canonical_aliases(orig_aliases_dict):
    # only put lowercase namespaces in items, and lowercase dois
    lowercase_aliases_dict = {}
    for orig_namespace in orig_aliases_dict:
        lowercase_namespace = clean_id(orig_namespace.lower())
        if lowercase_namespace == "doi":
            lowercase_aliases_dict[lowercase_namespace] = [clean_id(doi.lower()) for doi in orig_aliases_dict[orig_namespace]]
        else:
            lowercase_aliases_dict[lowercase_namespace] = [clean_id(nid) for nid in orig_aliases_dict[orig_namespace]]
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
    #logger.debug(u"in MERGE ALIAS DICTS with %s and %s" %(aliases1, aliases2))
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

    if host in ["dryad", "figshare"]:
        genre = "dataset"  #treat as dataset for the sake of normalization

    if genre not in myrefsets.keys():
        #logger.info(u"Genre {genre} not in refsets so give up".format(
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
            #logger.info(u"No good lookup in %s %s %s for %s" %(genre, refsetname, year, metric_name))
            pass
        except ValueError:
            logger.error(u"Exception: no good lookup in %s %s %s for %s" %(genre, refsetname, year, metric_name))
            logger.debug(u"Value error calculating percentiles for %s %s %s for %s=%s" %(genre, refsetname, year, metric_name, str(value)))
            logger.debug(u"fencepost = {fencepost_values}".format(
                fencepost_values=fencepost_values))
            pass
            
    return response

def retrieve_items(tiids, myrefsets, myredis, mydao):
    something_currently_updating = False
    items = []
    for tiid in tiids:
        try:
            item = get_item(tiid, myrefsets, myredis)
        except (LookupError, AttributeError), e:
            logger.warning(u"Got an error looking up tiid '{tiid}'; error: {error}".format(
                    tiid=tiid, error=e.__repr__()))
            raise

        if not item:
            logger.warning(u"Looks like there's no item with tiid '{tiid}': ".format(
                    tiid=tiid))
            raise LookupError
            
        item["currently_updating"] = is_currently_updating(tiid, myredis)
        something_currently_updating = something_currently_updating or item["currently_updating"]

        items.append(item)
    return (items, something_currently_updating)

def is_currently_updating(tiid, myredis):
    num_providers_currently_updating = myredis.get_num_providers_currently_updating(tiid)
    currently_updating = num_providers_currently_updating > 0
    return currently_updating

   
def create_item(namespace, nid, myredis, mydao):
    logger.debug(u"In create_item with alias" + str((namespace, nid)))
    item_doc = make()
    namespace = clean_id(namespace)
    nid = clean_id(nid)
    item_doc["aliases"][namespace] = [nid]
    item_doc["aliases"] = canonical_aliases(item_doc["aliases"])

    item_obj = create_objects_from_item_doc(item_doc)

    logger.info(u"saved new collection '{tiid}'".format(
            tiid=item_doc["_id"]))

    logger.debug(json.dumps(item_doc, sort_keys=True, indent=4))

    analytics_credentials = {}
    start_item_update(item_doc["_id"], item_doc["aliases"], analytics_credentials, myredis)

    logger.info(u"Created new item '{tiid}' with alias '{alias}'".format(
        tiid=item_doc["_id"],
        alias=str((namespace, nid))
    ))

    return item_doc["_id"]


def get_tiids_from_aliases(aliases):
    clean_aliases = [canonical_alias_tuple((ns, nid)) for (ns, nid) in aliases]
    aliases_tiid_mapping = {}

    for alias in clean_aliases:
        alias_key = alias
        tiid = None
        (ns, nid) = alias
        if (ns=="biblio"):
            alias_key = (ns, json.dumps(nid))
            tiid = get_tiid_by_biblio(nid)        
        else:
            alias_obj = Alias.query.filter_by(namespace=ns, nid=nid).first()
            try:
                tiid = alias_obj.tiid
                logger.debug(u"Found a tiid for {nid} in get_tiid_by_alias: {tiid}".format(
                    nid=nid, 
                    tiid=tiid))
            except AttributeError:
                pass
        aliases_tiid_mapping[alias_key] = tiid
    return aliases_tiid_mapping



def create_tiids_from_aliases(aliases, myredis):
    tiid_alias_mapping = {}
    clean_aliases = [canonical_alias_tuple((ns, nid)) for (ns, nid) in aliases]    
    for alias in clean_aliases:
        (ns, nid) = alias
        item_doc = make()
        if ns=="biblio":
            item_doc["aliases"][ns] = [nid]
        else:
            item_doc["aliases"][ns] = [nid]
        tiid = item_doc["_id"]

        logger.debug(u"in create_tiids_from_aliases for {tiid}, now to postgres".format(
            tiid=tiid))   
        item_obj = create_objects_from_item_doc(item_doc)
        db.session.merge(item_obj)

        tiid_alias_mapping[tiid] = alias

        analytics_credentials={}
        start_item_update(tiid, item_doc["aliases"], analytics_credentials, myredis)

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in create_tiids_from_aliases for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 

    return tiid_alias_mapping


def get_items_from_tiids(tiids):
    items = []
    for tiid in tiids:
        items += [Item.from_tiid(tiid)]
    return items


def get_tiid_by_biblio(biblio_dict):
    try:
        raw_sql = text("""select tiid from min_biblio 
                                        where title=:title
                                        and authors=:authors
                                        and journal=:journal""")
        biblio_statement = db.session.execute(raw_sql, params={
            "title":'"'+biblio_dict["title"]+'"',
            "authors":'"'+biblio_dict["authors"]+'"',
            "journal":'"'+biblio_dict["journal"]+'"'
            })
        biblio = biblio_statement.first()
        db.session.commit()
        tiid = biblio.tiid
    except AttributeError:
        logger.error(u"AttributeError in  get_tiid_by_biblio with {biblio_dict}".format(
            biblio_dict=biblio_dict))
        tiid = None

    return tiid

def get_tiid_by_alias(ns, nid, mydao=None):
    logger.debug(u"In get_tiid_by_alias with {ns}, {nid}".format(
        ns=ns, nid=nid))

    tiid = None
    if (ns=="biblio"):
        tiid = get_tiid_by_biblio(nid)
    else:
        # change input to lowercase etc
        (ns, nid) = canonical_alias_tuple((ns, nid))
        alias_obj = Alias.query.filter_by(namespace=ns, nid=nid).first()
        try:
            tiid = alias_obj.tiid
            logger.debug(u"Found a tiid for {nid} in get_tiid_by_alias: {tiid}".format(
                nid=nid, tiid=tiid))
        except AttributeError:
            pass

    if not tiid:
        logger.debug(u"no match for tiid for {nid}!".format(nid=nid))
    return tiid


def start_item_update(tiid, aliases_dict, analytics_credentials, myredis):
    logger.debug(u"In start_item_update with {tiid}, /biblio_print {aliases_dict}".format(
        tiid=tiid, aliases_dict=aliases_dict))
    myredis.init_currently_updating_status(tiid,
        ProviderFactory.providers_with_metrics(default_settings.PROVIDERS))
    myredis.add_to_alias_queue(tiid, aliases_dict, analytics_credentials)


