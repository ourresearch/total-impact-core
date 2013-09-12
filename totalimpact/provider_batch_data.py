import datetime, json, re, copy
from sqlalchemy.exc import IntegrityError
from totalimpact import db
from totalimpact import json_sqlalchemy

import logging
logger = logging.getLogger('ti.provider_batch_data')


class ProviderBatchData(db.Model):
    provider = db.Column(db.Text, primary_key=True)
    min_event_date = db.Column(db.DateTime(), primary_key=True)
    max_event_date = db.Column(db.DateTime())
    raw = db.Column(db.Text)
    aliases = db.Column(json_sqlalchemy.JSONAlchemy(db.Text))
    provider_raw_version = db.Column(db.Numeric)
    created = db.Column(db.DateTime())

    def __init__(self, **kwargs):
        self.created = datetime.datetime.utcnow()
        super(ProviderBatchData, self).__init__(**kwargs)

    def __repr__(self):
        return '<ProviderBatchData {provider}, {min_event_date}, {max_event_date}>'.format(
            provider=self.provider, 
            min_event_date=self.min_event_date, 
            max_event_date=self.max_event_date)

def create_objects_from_doc(doc):
    logger.debug(u"in create_objects_from_doc for {id}".format(
        id=doc["_id"]))        

    new_object = ProviderBatchData.query.filter_by(
        provider=doc["provider"], 
        min_event_date=doc["min_event_date"]).first()
    if not new_object:
        new_dict = copy.deepcopy(doc)
        del new_dict["_id"]
        if "_rev" in new_dict:
            del new_dict["_rev"]
        del new_dict["type"]
        new_object = ProviderBatchData(**new_dict)
    db.session.add(new_object)
    db.session.commit()

    return new_object


