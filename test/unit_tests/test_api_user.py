from totalimpact import api_user, tiredis
import os, json

from nose.tools import raises, assert_equals, nottest
import unittest


class TestApiUser():

    def setUp(self):
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

        self.sample_user_api_doc = {'key_history': {'2012-12-27T12:09:20.072080': 'SFUlqzam8'}, 'created': '2012-12-27T12:09:20.072080', 'current_key': 'SFUlqzam8', 
            'registered_items': {self.test_alias_registered_string: {"tiid":"tiid2", "registered_date":"2012etc"}}, 
            'max_registered_items':3,
            'meta': {'usage': 'individual CV', 'api_limit': '', 'notes': '', 'api_key_owner': '', 'email': ''}, '_id': 'XeZhf8BWNgM5r9B9Xu3whT', 'type': 'api_user'}
        self.d.db.save(self.sample_user_api_doc)       


    def test_build_api_user(self):
        meta = {'usage': 'individual CV', 'email': '', 'notes': '', 'api_limit': '', 'api_key_owner': ''}
        (new_api_doc, new_api_key) = api_user.build_api_user("SFU", 1000, **meta)
        print new_api_doc
        expected = self.sample_user_api_doc
        assert_equals(new_api_doc["current_key"], new_api_key)
        assert_equals(new_api_doc["meta"], expected["meta"])

    def test_get_api_user_id_by_api_key(self):
        expected_api_doc_id = self.sample_user_api_doc["_id"]
        api_key = self.sample_user_api_doc["current_key"]
        response_api_user_id = api_user.get_api_user_id_by_api_key(api_key, self.d)
        assert_equals(response_api_user_id, expected_api_doc_id)

    def test_is_registered(self):
        response = api_user.is_registered(self.test_alias, "SFUlqzam8", self.d)
        assert_equals(response, False)

        response = api_user.is_registered(self.test_alias_registered, "SFUlqzam8", self.d)
        assert_equals(response, True)

    @raises(api_user.InvalidApiKeyException)
    def test_register_item_invalid_key(self):
        api_user.register_item(self.test_alias, "INVALID_KEY", self.r, self.d)

    def test_is_over_quota(self):
        api_key = "SFUlqzam8"
        response = api_user.is_over_quota(api_key, self.d)
        assert_equals(response, False)

        api_user.add_registration_data(("doi", "10.a"), "tiida", api_key, self.d)
        api_user.add_registration_data(("doi", "10.b"), "tiidb", api_key, self.d)
        api_user.add_registration_data(("doi", "10.c"), "tiidc", api_key, self.d)
        response = api_user.is_over_quota(api_key, self.d)
        assert_equals(response, True)

    def test_register_item_success(self):
        api_key = "SFUlqzam8"
        response = api_user.is_registered(self.test_alias, api_key, self.d)
        assert_equals(response, False)

        tiid = api_user.register_item(self.test_alias, api_key, self.r, self.d)
        response = api_user.is_registered(self.test_alias, api_key, self.d)
        assert_equals(response, True)



