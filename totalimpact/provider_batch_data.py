import datetime, json, re
from sqlalchemy.exc import IntegrityError
from totalimpact import db

import logging
logger = logging.getLogger('ti.provider_batch_data')


class ProviderBatchData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime())
    min_event_date = db.Column(db.DateTime())
    max_event_date = db.Column(db.DateTime())
    raw = db.Column(db.Text)
    aliases = db.Column(db.Text)
    provider = db.Column(db.Text)
    provider_raw_version = db.Column(db.Numeric)

    def __init__(self, aliases, **kwargs):
        self.created = datetime.datetime.utcnow()
        super(ProviderBatchData, self).__init__(**kwargs)
        self.aliases = json.dumps(aliases)

    def __repr__(self):
        return '<ProviderBatchData {provider}, {min_event_date}, {max_event_date}>'.format(
            provider=self.provider, 
            min_event_date=self.min_event_date, 
            max_event_date=self.max_event_date)

