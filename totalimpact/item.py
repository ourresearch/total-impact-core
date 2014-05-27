from werkzeug import generate_password_hash, check_password_hash
import shortuuid, datetime, hashlib, threading, json, time, copy, re
from collections import defaultdict
from celery.result import AsyncResult

from totalimpact.providers.provider import ProviderFactory
from totalimpact.providers.provider import ProviderTimeout, ProviderServerError
from totalimpact.providers.provider import normalize_alias
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


def create_biblio_objects(list_of_old_style_biblio_dicts, provider=None, collected_date=datetime.datetime.utcnow()):
    new_biblio_objects = []

    provider_number = 0
    for biblio_dict in list_of_old_style_biblio_dicts:
        if not provider:
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


def create_objects_from_item_doc(item_doc, skip_if_exists=False, commit=True):
    tiid = item_doc["_id"]

    # logger.debug(u"in create_objects_from_item_doc for {tiid}".format(
    #     tiid=item_doc["_id"]))        

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
        new_biblio_objects = create_biblio_objects(alias_dict["biblio"], provider=None, collected_date=item_doc["last_modified"]) 
        new_item_object.biblios = new_biblio_objects

    new_metric_objects = None
    if "metrics" in item_doc:
        new_metric_objects = create_metric_objects(item_doc["metrics"]) 
        for metric in new_metric_objects:
            metric.tiid = item_doc["_id"]
            db.session.add(metric)

    if commit:
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
    query_type = None

    def __init__(self, **kwargs):
        if "collected_date" in kwargs:
            self.collected_date = kwargs["collected_date"]
        else:
            self.collected_date = datetime.datetime.utcnow()
        if "query_type" in kwargs:
            self.query_type = kwargs["query_type"]
        super(Metric, self).__init__(**kwargs)

    @property
    def fully_qualified_name(self):
        return "{provider}:{metric_name}".format(
            provider=self.provider, metric_name=self.metric_name)

    def __repr__(self):
        return '<Metric {tiid} {provider}:{metric_name}={raw_value} on {collected_date} via {query_type}>'.format(
            provider=self.provider, 
            metric_name=self.metric_name, 
            raw_value=self.raw_value, 
            collected_date=self.collected_date, 
            query_type=self.query_type,
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
            shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')
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
    def from_tiid(cls, tiid, with_metrics=True):
        item = cls.query.get(tiid)
        if not item:
            return None
        if with_metrics:
            item.metrics = item.metrics_query.all()
        return item

    @property
    def alias_tuples(self):
        return [alias.alias_tuple for alias in self.aliases]

    @property
    def biblio_dict(self):
        response = {}
        for biblio in self.biblios:
            response[biblio.biblio_name] = biblio.biblio_value
        return response

    @property
    def biblio_dicts_per_provider(self):
        response = defaultdict(dict)
        for biblio in self.biblios:
            response[biblio.provider][biblio.biblio_name] = biblio.biblio_value
        return response        

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

    def has_user_provided_biblio(self):
        return any([biblio.provider=='user_provided' for biblio in self.biblios])

    def has_free_fulltext_url(self):
        return any([biblio.biblio_name=='free_fulltext_url' for biblio in self.biblios])

    @classmethod
    def create_from_old_doc(cls, doc):
        # logger.debug(u"in create_from_old_doc for {tiid}".format(
        #     tiid=doc["_id"]))

        doc_copy = copy.deepcopy(doc)
        doc_copy["tiid"] = doc_copy["_id"]
        for key in doc_copy.keys():
            if key not in ["tiid", "created", "last_modified", "last_update_run"]:
                del doc_copy[key]
        new_item_object = Item(**doc_copy)

        return new_item_object

    @property
    def biblio_dict(self):
        biblio_dict = {}
        for biblio_obj in self.biblios:
            if (biblio_obj.biblio_name not in biblio_dict) or (biblio_obj.provider == "user_provided"):
                    biblio_dict[biblio_obj.biblio_name] = biblio_obj.biblio_value    
        return biblio_dict

    def as_old_doc(self):
        # logger.debug(u"in as_old_doc for {tiid}".format(
        #     tiid=self.tiid))

        item_doc = {}
        item_doc["_id"] = self.tiid
        item_doc["last_modified"] = self.last_modified.isoformat()
        item_doc["created"] = self.created.isoformat()
        item_doc["last_update_run"] = self.last_update_run.isoformat()
        item_doc["type"] = "item"

        item_doc["biblio"] = self.biblio_dict

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

    if not item_obj:
        return None
    try:
        item_for_client = build_item_for_client(item_obj, myrefsets, myredis)
    except Exception, e:
        item_for_client = None
        logger.error(u"Exception %s: Skipping item, unable to build %s, %s" % (e.__repr__(), tiid, str(item_for_client)))
    return item_for_client



def diff_for_dict_metrics(previous_json, current_json):
    previous = json.loads(previous_json)
    current = json.loads(current_json)
    diff = []
    min_value_previous = min([entry["value"] for entry in previous])
    previous_dict = dict((entry["name"], entry["value"]) for entry in previous)
    for entry in current:
        if entry["name"] in previous_dict:
            previous_value = previous_dict[entry["name"]]
        else:
            previous_value = min_value_previous
        diff += [{"name": entry["name"], "value": entry["value"] - previous_value}]
    if max([entry["value"] for entry in diff]) == 0:
        return None
    else:
        return diff


def build_item_for_client(item_metrics_dict, myrefsets, myredis):
    item_obj = item_metrics_dict["item_obj"]
    metrics_summaries = item_metrics_dict["metrics_summaries"]
    item = item_obj.as_old_doc()

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

    metrics = defaultdict(dict)

    for fully_qualified_metric_name in metrics_summaries:
        try:
            most_recent_metric_obj = metrics_summaries[fully_qualified_metric_name]["most_recent"]
            metric_name = fully_qualified_metric_name
            metrics[metric_name]["provenance_url"] = most_recent_metric_obj.drilldown_url
        except (KeyError, ValueError, AttributeError, TypeError):
            metric_name = None

        if metric_name and (metric_name in all_static_meta.keys()):  # make sure we still support this metrics type
            # add static data

            metrics[metric_name]["static_meta"] = all_static_meta[metric_name]  

            if most_recent_metric_obj:
                metrics[metric_name]["historical_values"] = {}
                raw = as_int_or_float_if_possible(most_recent_metric_obj.raw_value)
                if isinstance(raw, basestring):
                    try:
                        raw = json.loads(raw)
                    except ValueError:
                        pass

                metrics[metric_name]["historical_values"]["current"] = {
                        "collected_date": most_recent_metric_obj.collected_date.isoformat(),
                        "raw": raw
                        }

                metrics[metric_name]["values"] = {"raw": raw}
                earlier_metric_obj = None
                raw_diff = None

                try:
                    earlier_metric_obj = metrics_summaries[fully_qualified_metric_name]["7_days_ago"]
                    earlier_metric_raw = as_int_or_float_if_possible(earlier_metric_obj.raw_value)
                    metrics[metric_name]["historical_values"]["previous"] = {
                            "collected_date": earlier_metric_obj.collected_date.isoformat(),
                            "raw": earlier_metric_raw
                            }
                    raw_diff = raw - earlier_metric_raw
                except (KeyError, ValueError, AttributeError, TypeError):
                    # try:
                    #     raw_diff = diff_for_dict_metrics(earlier_metric_obj.raw_value, most_recent_metric_obj.raw_value)
                    # except (KeyError, ValueError, AttributeError, TypeError):
                    #     pass
                    metrics[metric_name]["historical_values"]["previous"] = {
                            "collected_date": None,
                            "raw": None
                            }

                try:
                    # need to round the dates because python difference returns number of full days between
                    rounded_recent_date = most_recent_metric_obj.collected_date.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
                    rounded_earlier_date = earlier_metric_obj.collected_date.replace(hour = 0, minute = 0, second = 0, microsecond = 0)

                    raw_diff_days = (rounded_recent_date - rounded_earlier_date).days
                except (KeyError, ValueError, AttributeError, TypeError):
                    item_created_date = item_obj.created.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
                    raw_diff_days = (rounded_recent_date - item_created_date).days

                    if raw_diff_days > 7:
                        raw_diff = raw
                        raw_diff_days = 7.2  # special value, assumes that things are updated once a week and this is first metric

                metrics[metric_name]["historical_values"]["diff"] = {
                    "days": raw_diff_days,
                    "raw": raw_diff
                    }
    
                try:
                    # add normalization values
                    # need year to calculate normalization below
                    year = int(item["biblio"]["year"])
                    if year < 2002:
                        year = 2002
                    normalized_values = get_normalized_values(genre, host, year, metric_name, raw, myrefsets)
                    metrics[metric_name]["values"].update(normalized_values)
                except (KeyError, ValueError, AttributeError):
                    #logger.error(u"No good year in biblio for item {tiid}, no normalization".format(
                    #    tiid=item["_id"]))
                    pass


    # ditch metrics we don't have static_meta for:

    item["metrics"] = {k:v for k, v in metrics.iteritems() if "static_meta" in v}
    item["update_status"] = update_status(item["_id"], myredis)

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




def add_metric_to_item_object(full_metric_name, metrics_method_response, item_obj):
    tiid = item_obj.tiid

    (metric_value, provenance_url) = metrics_method_response
    (provider, metric_name) = full_metric_name.split(":")

    new_style_metric_dict = {
        "tiid": tiid,
        "metric_name": metric_name, 
        "provider": provider, 
        "raw_value": as_int_or_float_if_possible(metric_value),
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

    return item_obj




def add_aliases_to_item_object(aliases_dict, item_obj):
    logger.debug(u"in add_aliases_to_item_object for {tiid}".format(
        tiid=item_obj.tiid))        

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


def add_biblio(tiid, biblio_name, biblio_value, provider_name="user_provided", collected_date=datetime.datetime.utcnow()):

    logger.debug(u"in add_biblio for {tiid} {biblio_name}".format(
        tiid=tiid, biblio_name=biblio_name))

    biblio_object = Biblio.query.filter_by(tiid=tiid, provider=provider_name, biblio_name=biblio_name).first()
    if biblio_object:
        logger.debug(u"found a previous row in add_biblio for {tiid} {biblio_name}, so removing it".format(
            tiid=tiid, biblio_name=biblio_name))
        biblio_object.biblio_value = biblio_value
        biblio_object.collected_date = collected_date
    else:
        biblio_object = Biblio(tiid=tiid, 
                biblio_name=biblio_name, 
                biblio_value=biblio_value, 
                provider=provider_name, 
                collected_date=collected_date)
        db.session.add(biblio_object)

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_biblio for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 

    logger.debug(u"finished saving add_biblio for {tiid} {biblio_name}".format(
        tiid=tiid, biblio_name=biblio_name))

    item_obj = Item.from_tiid(tiid)

    logger.debug(u"got object for add_biblio for {tiid} {biblio_name}".format(
        tiid=tiid, biblio_name=biblio_name))

    return item_obj



def add_biblio_to_item_object(new_biblio_dict, item_doc, provider_name):
    tiid = item_doc["_id"]
    item_obj = Item.from_tiid(tiid)

    logger.debug(u"in add_biblio_to_item_object for {tiid} {provider_name}, /biblio_print {new_biblio_dict}".format(
        tiid=tiid, 
        provider_name=provider_name,
        new_biblio_dict=new_biblio_dict))        

    new_biblio_objects = create_biblio_objects([new_biblio_dict], provider=provider_name)
    for new_biblio_obj in new_biblio_objects:
        if not Biblio.query.get((tiid, provider_name, new_biblio_obj.biblio_name)):
            item_obj.biblios += [new_biblio_obj]    

    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_biblio_to_item_object for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 
        
    return item_obj



def get_biblio_to_update(old_biblio, new_biblio):
    if not old_biblio:
        return new_biblio

    response = {}
    for biblio_name in new_biblio:
        if not biblio_name in old_biblio:
            response[biblio_name] = new_biblio[biblio_name]

        # a few things should get overwritten no matter what
        if (biblio_name=="title") and ("title" in old_biblio):
            if old_biblio["title"] == "AOP":
                response[biblio_name] = new_biblio[biblio_name]

        if (biblio_name in ["is_oa_journal", "oai_id", "free_fulltext_url"]):
            response[biblio_name] = new_biblio[biblio_name]

    return response



def update_item_with_new_biblio(new_biblio_dict, item_obj, provider_name=None):
    item_doc = item_obj.as_old_doc()

    # return None if no changes
    # don't change if biblio already there, except in special cases

    response = get_biblio_to_update(item_doc["biblio"], new_biblio_dict)
    if response:
        item_doc["biblio"] = response
        item_obj = add_biblio_to_item_object(new_biblio_dict, item_doc, provider_name=provider_name)
    return(item_obj)


def make():
    now = datetime.datetime.utcnow().isoformat()
    shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')

    item = {}
    item["_id"] = shortuuid.uuid()[0:24]
    item["aliases"] = {}
    item["biblio"] = {}
    item["last_modified"] = now
    item["created"] = now
    item["type"] = "item"
    return item


def clean_for_export(item, supplied_key=None, secret_key=None, override_export_clean=False):
    if not override_export_clean and supplied_key and (supplied_key==secret_key):
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

    elif "arxiv" in alias_dict:
        genre = "article"
        host = "arxiv"

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

    # override if it came in with a genre, or call it an "article" if it has a journal
    if (host=="unknown" and ("biblio" in alias_dict)):
        for biblio_dict in alias_dict["biblio"]:
            if "genre" in biblio_dict and (biblio_dict["genre"] not in ["undefined", "other"]):
                genre = biblio_dict["genre"]
            elif ("journal" in biblio_dict) and biblio_dict["journal"]:  
                genre = "article"

    if "article" in genre:
        genre = "article"  #disregard whether journal article or conference article for now

    return (genre, host)


def canonical_alias_tuple(alias):
    (namespace, nid) = alias
    namespace = clean_id(namespace)
    nid = clean_id(nid)
    namespace = namespace.lower()
    if namespace=="doi":
        try:
            nid = nid.lower()
        except AttributeError:
            pass
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
            
        item["update_status"] = update_status(tiid, myredis)
        something_currently_updating = something_currently_updating or (item["update_status"] != "SUCCESS")

        items.append(item)
    return (items, something_currently_updating)

def update_status_from_task_id(task_id, tiid=None):
    update_status = "SUCCESS: no recent update"
    if task_id:
        if task_id.lower() == "start":
            update_status = "start_queueing"
        else:
            task_result = AsyncResult(task_id)
            try:
                if task_result.ready():
                    update_status = task_result.state
                else:
                    update_status = task_result.state
            except AttributeError:
                update_status = "WAITING" # tasks's task not done yet
                pass
    if not update_status.startswith("SUCCESS"):
        # logger.debug(u"update_status: task_id={task_id}, update_status={update_status}, tiid={tiid}".format(
        #     task_id=task_id, update_status=update_status, tiid=tiid))
        pass
    return update_status

def update_status(tiid, myredis):
    task_id = myredis.get_task_id(tiid)
    return update_status_from_task_id(task_id, tiid)

   
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

    start_item_update([{"tiid":item_doc["_id"], "aliases_dict":item_doc["aliases"]}], "low", myredis)

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


# forgoes some checks for speed because only used for just-created items
def add_alias_to_new_item(alias_tuple, provider=None):
    item_obj = Item()
    (namespace, nid) = alias_tuple
    if namespace=="biblio":
        if not provider:
            provider = "unknown1"
        for biblio_name in nid:
                biblio_object = Biblio(biblio_name=biblio_name, 
                        biblio_value=nid[biblio_name], 
                        provider=provider)
                item_obj.biblios += [biblio_object]
    else:
        item_obj.aliases = [Alias(alias_tuple=alias_tuple)]
    return item_obj  


def create_tiids_from_aliases(aliases, analytics_credentials, myredis, provider=None):
    tiid_alias_mapping = {}
    clean_aliases = [canonical_alias_tuple((ns, nid)) for (ns, nid) in aliases]  
    dicts_to_update = []  

    logger.debug(u"in create_tiids_from_aliases, starting alias loop")

    for alias_tuple in clean_aliases:
        logger.debug(u"in create_tiids_from_aliases, with alias_tuple {alias_tuple}".format(
            alias_tuple=alias_tuple))
        item_obj = add_alias_to_new_item(alias_tuple, provider)
        tiid = item_obj.tiid
        db.session.add(item_obj)
        # logger.debug(u"in create_tiids_from_aliases, made item {item_obj}".format(
        #     item_obj=item_obj))

        tiid_alias_mapping[tiid] = alias_tuple
        dicts_to_update += [{"tiid":tiid, "aliases_dict": alias_dict_from_tuples([alias_tuple])}]

    logger.debug(u"in create_tiids_from_aliases, starting commit")
    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in create_tiids_from_aliases for {tiid}, rolling back.  Message: {message}".format(
            tiid=tiid, 
            message=e.message)) 

    # has to be after commits to database
    logger.debug(u"in create_tiids_from_aliases, starting start_item_update")
    start_item_update(dicts_to_update, "high", myredis)

    logger.debug(u"in create_tiids_from_aliases, finished")
    return tiid_alias_mapping


def get_items_from_tiids(tiids, with_metrics=True):
    items = []
    for tiid in tiids:
        item = Item.from_tiid(tiid, with_metrics)
        if item:
            items += [item]
        else:
            logger.warning(u"in get_items_from_tiids, no item found for tiid {tiid}".format(
                tiid=tiid))

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
        logger.error(u"AttributeError in get_tiid_by_biblio with {biblio_dict}".format(
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


def start_item_update(dicts_to_add, priority, myredis):
    # logger.debug(u"In start_item_update with {tiid}, priority {priority} /biblio_print {aliases_dict}".format(
    #     tiid=tiid, priority=priority, aliases_dict=aliases_dict))
    myredis.set_tiid_task_ids(dict((d["tiid"], "START") for d in dicts_to_add))
    for d in dicts_to_add:
        # this import here to avoid circular dependancies
        from tasks import put_on_celery_queue
        task_id = put_on_celery_queue(d["tiid"], d["aliases_dict"], priority)
    


def is_equivalent_alias_tuple_in_list(query_tuple, tuple_list):
    is_equivalent = (clean_alias_tuple_for_deduplication(query_tuple) in tuple_list)
    return is_equivalent

def clean_alias_tuple_for_deduplication(alias_tuple):
    (ns, nid) = alias_tuple
    if ns == "biblio":
        keys_to_compare = ["full_citation", "title", "authors", "journal", "year"]
        if not isinstance(nid, dict):
            nid = json.loads(nid)
        if "year" in nid:
            nid["year"] = str(nid["year"])
        biblio_dict_for_deduplication = dict([(k, v) for (k, v) in nid.iteritems() if k.lower() in keys_to_compare])

        biblios_as_string = json.dumps(biblio_dict_for_deduplication, sort_keys=True, indent=0, separators=(',', ':'))
        return ("biblio", biblios_as_string.lower())
    else:
        (ns, nid) = normalize_alias((ns, nid))
        try:
            cleaned_alias = (ns.lower(), nid.lower())
        except AttributeError:
            logger.debug(u"problem cleaning {alias_tuple}".format(
                alias_tuple=alias_tuple))
            cleaned_alias = alias_tuple
        return cleaned_alias


def alias_tuples_for_deduplication(item):
    alias_tuples = []
    if item.aliases:
        alias_tuples = [alias.alias_tuple for alias in item.aliases]
    biblio_dicts_per_provider = item.biblio_dicts_per_provider
    for provider in biblio_dicts_per_provider:
        alias_tuple = ("biblio", biblio_dicts_per_provider[provider])
        alias_tuples += [alias_tuple]
        # logger.debug(u"tiid={tiid}, for provider {provider} is a new alias {alias_tuple}".format(
        #     tiid=item.tiid, provider=provider, alias_tuple=alias_tuple))

    cleaned_tuples = [clean_alias_tuple_for_deduplication(alias_tuple) for alias_tuple in alias_tuples]
    cleaned_tuples = [alias_tuple for alias_tuple in cleaned_tuples if alias_tuple != ("biblio", '{}')]

    # logger.debug(u"tiid={tiid}, cleaned_tuples {cleaned_tuples}".format(
    #     tiid=item.tiid, cleaned_tuples=cleaned_tuples))
    return cleaned_tuples

def aliases_not_in_existing_tiids(retrieved_aliases, existing_tiids):
    new_aliases = []
    if not existing_tiids:
        return retrieved_aliases
    existing_items = Item.query.filter(Item.tiid.in_(existing_tiids)).all()

    aliases_from_all_items = []
    for item in existing_items:
        logger.debug(u"getting alias_tuples_for_deduplication for tiid={tiid}".format(
             tiid=item.tiid))
        aliases_from_all_items += alias_tuples_for_deduplication(item)

    for alias_tuple in retrieved_aliases:
        if is_equivalent_alias_tuple_in_list(alias_tuple, aliases_from_all_items):
            # logger.debug(u"already have alias {alias_tuple}".format(
            #     alias_tuple=alias_tuple))
            pass
        else:
            new_aliases += [alias_tuple]
            # logger.debug(u"is a new alias {alias_tuple}".format(
            #     alias_tuple=alias_tuple))
    return new_aliases


def build_duplicates_list(tiids):
    items = get_items_from_tiids(tiids, with_metrics=False)
    distinct_groups = defaultdict(list)
    duplication_list = {}
    for item in items:
        is_distinct_item = True

        alias_tuples = alias_tuples_for_deduplication(item)

        for alias in alias_tuples:

            if is_equivalent_alias_tuple_in_list(alias, duplication_list):
                # we already have one of the aliase
                distinct_item_id = duplication_list[clean_alias_tuple_for_deduplication(alias)] 
                is_distinct_item = False  

        if is_distinct_item:
            distinct_item_id = len(distinct_groups)
            for alias in alias_tuples:
                # we went through all the aliases and don't have any that match, so make a new entries
                duplication_list[clean_alias_tuple_for_deduplication(alias)] = distinct_item_id

        # whether distinct or not,
        # add this to the group, and add all its aliases too
        if item.created:
            created_date = item.created.isoformat()
        else:
            created_date = "1999-01-01T14:42:49.818393"   
        distinct_groups[distinct_item_id] += [{ "tiid":item.tiid, 
                                                "has_user_provided_biblio":item.has_user_provided_biblio(), 
                                                "has_free_fulltext_url":item.has_free_fulltext_url(), 
                                                "created":created_date
                                                }]

    distinct_groups_values = [group for group in distinct_groups.values() if group]
    return distinct_groups_values

