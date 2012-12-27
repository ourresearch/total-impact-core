from totalimpact import api_user
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

        self.sample_user_api_doc = {'key_history': {'2012-12-27T12:09:20.072080': 'SFUlqzam8'}, 'created': '2012-12-27T12:09:20.072080', 'current_key': 'SFUlqzam8', 'registered_items': {}, 'max_registered_items': 1000, 'meta': {'usage': 'individual CV', 'api_limit': '', 'notes': '', 'api_key_owner': '', 'email': ''}, '_id': 'XeZhf8BWNgM5r9B9Xu3whT', 'type': 'api_user'}
        self.d.db.save(self.sample_user_api_doc)       

    def test_build_api_user(self):
        meta = {'usage': 'individual CV', 'email': '', 'notes': '', 'api_limit': '', 'api_key_owner': ''}
        (new_api_doc, new_api_key) = api_user.build_api_user("SFU", **meta)
        print new_api_doc
        expected = self.sample_user_api_doc
        assert_equals(new_api_doc["current_key"], new_api_key)
        assert_equals(new_api_doc["meta"], expected["meta"])

    def test_get_api_user_id_by_api_key(self):
        expected_api_doc_id = self.sample_user_api_doc["_id"]
        api_key = self.sample_user_api_doc["current_key"]
        response_api_user_id = api_user.get_api_user_id_by_api_key(api_key, self.d)
        assert_equals(response_api_user_id, expected_api_doc_id)

    def test_register_item(self):
        meta = {'usage': 'individual CV', 'email': '', 'notes': '', 'api_limit': '', 'api_key_owner': ''}
        (api_user_doc, api_key) = api_user.build_api_user("UBC", **meta)
        self.d.db.save(api_user_doc)       

        alias1 = "10.1371/journal.pcbi.1"
        tiid1 = "tiid1"
        remaining_registration_spots = api_user.register_item(alias1, tiid1, api_key, self.d)
        assert_equals(remaining_registration_spots, 999)

        alias2 = "10.1371/journal.pcbi.2"
        tiid2 = "tiid2"
        remaining_registration_spots = api_user.register_item(alias2, tiid2, api_key, self.d)
        assert_equals(remaining_registration_spots, 998)



