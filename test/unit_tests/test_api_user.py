from totalimpact import tiredis
from totalimpact import db, app
from totalimpact import api_user
from totalimpact.api_user import ApiUser, RegisteredItem

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

import os, json, copy

from nose.tools import raises, assert_equals, nottest
import unittest

class TestApiUser():

    def setUp(self):
        if not "localhost" in app.config["SQLALCHEMY_DATABASE_URI"]:
            assert(False), "Not running this unittest because SQLALCHEMY_DATABASE_URI is not on localhost"

        self.db = db
        try:
            self.db.drop_all()
        except OperationalError, e:  #database "database" does not exist
            print e
            pass
        self.db.create_all()

        from totalimpact import dao

        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.d.update_design_doc()

        # setup a clean new redis test database.  We're putting unittest redis at DB Number 8.
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()

        self.test_alias = ("doi", "10.1371/journal.pcbi.1")
        self.test_alias_registered = ("doi", "10.1371/journal.pcbi.2")
        self.test_alias_registered_string = ":".join(self.test_alias_registered)

        self.test_email = 'new_api_user@example.com'
        self.test_meta = {    
                    'max_registered_items': 3, 
                    'planned_use': 'individual CV', 
                    'email': self.test_email, 
                    'notes': '', 
                    'api_key_owner': 'Julia Smith', 
                    "example_url":"", 
                    "organization":"NASA"
                }

        api_key_prefix = "SFU"
        test_meta2 = copy.deepcopy(self.test_meta)
        test_meta2["email"] = 'existing_api_user@example.com'
        self.existing_api_user = ApiUser(api_key_prefix, **test_meta2)

        self.existing_registered_item = RegisteredItem(self.test_alias_registered, self.existing_api_user)

        self.db.session.add(self.existing_api_user)
        self.db.session.add(self.existing_registered_item)
        self.db.session.commit()
        self.db.session.flush()                


    def tearDown(self):
        self.db.session.close_all()

    def test_make_api_user(self):
        #make sure nothing there beforehand
        matching_api_users = ApiUser.query.filter_by(email=self.test_email).first()
        assert_equals(matching_api_users, None)

        api_key_prefix = "SFU"
        new_api_user = ApiUser(api_key_prefix, **self.test_meta)
        new_api_key = new_api_user.api_key        
        print new_api_user

        # still not there
        matching_api_users = ApiUser.query.filter_by(email=self.test_email).first()
        assert_equals(matching_api_users, None)

        self.db.session.add(new_api_user)
        self.db.session.commit()
        self.db.session.flush()

        # and now poof there it is
        matching_api_users = ApiUser.query.filter_by(email=self.test_email).first()
        assert_equals(matching_api_users.email, self.test_email)

        matching_api_users = ApiUser.query.filter_by(api_key=new_api_key).first()
        assert_equals(matching_api_users.api_key, new_api_key)


    def test_is_valid_key(self):
        response = api_user.is_valid_key("NOTVALID")
        assert_equals(response, False)

        response = api_user.is_valid_key("samplekey")
        assert_equals(response, True)

        response = api_user.is_valid_key(self.existing_api_user.api_key)
        assert_equals(response, True)



    def test_is_registered(self):
        response = api_user.is_registered(self.test_alias, "NOT_VALID_KEY")
        assert_equals(response, False)

        response = api_user.is_registered(self.test_alias_registered, self.existing_api_user.api_key)
        assert_equals(response, True)


    @raises(api_user.InvalidApiKeyException)
    def test_register_item_invalid_key(self):
        api_user.register_item(self.test_alias, "INVALID_KEY", self.r, self.d)


    def test_is_over_quota(self):
        api_key = self.existing_api_user.api_key
        response = api_user.is_over_quota(api_key)
        assert_equals(response, False)

        for x in ["a", "b", "c"]:  # max_registered_items was set to 3 for this test api_user
            response = api_user.register_item(("doi", "10."+x), api_key, self.r, self.d)
            if response["registered_item"]:
                print response["registered_item"]
                self.db.session.add(response["registered_item"])

        self.db.session.commit()
        self.db.session.flush()                

        response = api_user.is_over_quota(api_key)
        assert_equals(response, True)


    def test_register_item_success(self):
        existing_api_key = self.existing_api_user.api_key

        response = api_user.is_registered(self.test_alias, existing_api_key)
        assert_equals(response, False)

        response = api_user.register_item(self.test_alias, existing_api_key, self.r, self.d)
        assert_equals(response["registered_item"].alias, ('doi', '10.1371/journal.pcbi.1'))

        self.db.session.add(self.existing_registered_item)
        self.db.session.commit()
        self.db.session.flush()                

        response = api_user.is_registered(self.test_alias, existing_api_key)
        assert_equals(response, True)



