from totalimpact import api_user, dao
import os, json

from nose.tools import raises, assert_equals, nottest
import unittest


class TestApiUser():

    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.d.update_design_doc()

    def test_make(self):
        meta = {'usage': 'individual CV', 'email': '', 'notes': '', 'api_limit': '', 'api_key_owner': ''}
        (new_api_doc, new_api_key) = api_user.make("UBC", **meta)
        assert_equals(new_api_doc.keys(), ['key_history', 'created', 'current_key', 'registered_items', 'meta', 'type'])
        assert_equals(new_api_doc["current_key"], new_api_key)

    def test_register_item(self):
        pass

    def test_number_of_remaining_registration_spots(self):
        pass


