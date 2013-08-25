import datetime, shortuuid, os
import analytics
from sqlalchemy.exc import IntegrityError

from totalimpact import item
from totalimpact import db


import logging
logger = logging.getLogger('ti.api_user')


class ApiLimitExceededException(Exception):
    pass

class InvalidApiKeyException(Exception):
    pass

class ItemAlreadyRegisteredToThisKey(Exception):
    pass

class RegisteredItem(db.Model):
    api_key = db.Column(db.Text, db.ForeignKey('api_user.api_key'), primary_key=True)
    api_user = db.relationship('ApiUser',
        backref=db.backref('registered_items', lazy='dynamic'))
    alias = db.Column(db.Text, primary_key=True)
    registered_date = db.Column(db.DateTime())

    def __init__(self, alias, api_user):
        super(RegisteredItem, self).__init__()
        alias = item.canonical_alias_tuple(alias)
        alias_string = ":".join(alias)
        self.alias = alias_string
        self.api_user = api_user
        self.registered_date = datetime.datetime.utcnow()

    def __repr__(self):
        return '<RegisteredItem {api_key}, {alias}>'.format(
            api_key=self.api_user.api_key, 
            alias=self.alias)


class ApiUser(db.Model):
    api_key = db.Column(db.Text, primary_key=True)
    created = db.Column(db.DateTime())
    planned_use = db.Column(db.Text)
    example_url = db.Column(db.Text)
    api_key_owner = db.Column(db.Text)
    notes = db.Column(db.Text)
    api_key_owner = db.Column(db.Text)
    email = db.Column(db.Text)
    organization = db.Column(db.Text)
    max_registered_items = db.Column(db.Numeric)  # should be Integer, is Numeric to keep consistent with previous table

    def __init__(self, prefix, **kwargs):
        super(ApiUser, self).__init__(**kwargs)
        self.api_key = self.make_api_key(prefix)
        self.created = datetime.datetime.utcnow()

    def __repr__(self):
        return '<ApiUser {api_key}, {email}, {api_key_owner}>'.format(
            api_key=self.api_key, 
            api_key_owner=self.api_key_owner, 
            email=self.email)

    def make_api_key(self, prefix):
        new_api_key = prefix + "-" + shortuuid.uuid()[0:6]
        new_api_key = new_api_key.lower()
        return new_api_key



def get_api_user(key):
    if not key:
        return None
    match = ApiUser.query.filter_by(api_key=key.lower()).first()
    return match

def is_current_api_user_key(key):
    api_user = get_api_user(key)
    if api_user:
        return True
    return False

def is_internal_key(key):
    if not key:
        return False
    # make sure these are all lowercase because that is how they come in from flask
    if key.lower() in ["yourkey", "samplekey", "item-report-page", "api-docs", os.getenv("API_KEY").lower()]:
        return True
    return False


def is_valid_key(key):
    # do quick and common check first
    if is_internal_key(key):
        return True
    if is_current_api_user_key(key):
        return True
    return False


def get_registered_item(alias, api_key):
    api_user = get_api_user(api_key)
    if not api_user:
        return False
    print api_user
    print api_user.registered_items.first()

    alias = item.canonical_alias_tuple(alias)
    alias_string = ":".join(alias)
    matching_registered_item = api_user.registered_items.filter_by(alias=alias_string).first()
    return matching_registered_item


def is_registered(alias, api_key):
    matching_registered_item = get_registered_item(alias, api_key)
    if matching_registered_item:
        return True
    return False


def get_remaining_registration_spots(api_key):
    api_user = get_api_user(api_key)
    if not api_user:
        raise InvalidApiKeyException

    max_registered_items = api_user.max_registered_items
    used_registration_spots = len(api_user.registered_items.all())

    remaining_registration_spots = max_registered_items - used_registration_spots
    return remaining_registration_spots


def is_over_quota(api_key):
    try:
        remaining_registration_spots = get_remaining_registration_spots(api_key)
    except InvalidApiKeyException:
        return None
    if remaining_registration_spots <= 0:
        return True
    return False

def register_item(alias, api_key, myredis, mydao):
    if not is_valid_key(api_key):
        raise InvalidApiKeyException
    if is_registered(alias, api_key):
        raise ItemAlreadyRegisteredToThisKey

    registered_item = None
    (namespace, nid) = alias
    tiid = item.get_tiid_by_alias(namespace, nid, mydao)
    if not tiid:
        if is_over_quota(api_key):
            analytics.track("CORE", "Raised Exception", {
                "exception class": "ApiLimitExceededException",
                "api_key": api_key
                })
            raise ApiLimitExceededException
        else:
            tiid = item.create_item(namespace, nid, myredis, mydao)
            analytics.identify(api_key, {"name": api_key, 
                                        "api_user": True})
            analytics.track(api_key, "Created item because of registration", {
                "tiid": tiid,
                "namespace": namespace,
                "nid": nid,
                "api_key": api_key
                })

    api_user = get_api_user(api_key)
    if api_user:
        registered_item = RegisteredItem(alias, api_user)
    return {"tiid":tiid, "registered_item":registered_item}


