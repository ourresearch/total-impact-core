import os, unittest, time, json
from urllib import quote_plus
from nose.tools import nottest, assert_equals
from copy import deepcopy

from totalimpact.config import Configuration
from totalimpact import dao, api
from totalimpact.tilogging import logging

PLOS_TEST_DOI = "10.1371/journal.pone.0004803"
DRYAD_TEST_DOI = "10.5061/dryad.7898"
GITHUB_TEST_ID = "homebrew"
TEST_COLLECTION_ID = "TestCollectionId"
TEST_COLLECTION_TIID_LIST = ["tiid1", "tiid2"]
TEST_COLLECTION_TIID_LIST_MODIFIED = ["tiid1", "tiid_different"]
TEST_COLLECTION_NAME = "My Collection"
TEST_COLLECTION_OWNER = "Sally Smith"

class TestCollection(unittest.TestCase):

    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True 
        self.client = self.app.test_client()

        # setup the database
        self.testing_db_name = "collection_test"
        self.old_db_name = self.app.config["DB_NAME"]
        self.app.config["DB_NAME"] = self.testing_db_name
        self.d = dao.Dao(self.testing_db_name, self.app.config["DB_URL"],
            self.app.config["DB_USERNAME"], self.app.config["DB_PASSWORD"])

        self.d.create_new_db_and_connect(self.testing_db_name)

    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name


    def test_collection(self):
        self.d.create_new_db_and_connect(self.testing_db_name) 

        collection_items = []
        collection_items.append(["doi", quote_plus(PLOS_TEST_DOI)])
        collection_items.append(["doi", quote_plus(DRYAD_TEST_DOI)])

        # Post a new item
        response = self.client.post('/collection', 
                data=json.dumps(collection_items), 
                content_type="application/json")
        assert_equals(response.status_code, 201)  #Created
        response_loaded = json.loads(response.data)
        assert_equals(len(response_loaded["id"]), 6)
        new_collection_id = response_loaded["id"]

        # Try to get it 
        response = self.client.get('/collection/' + new_collection_id)
        assert_equals(response.status_code, 200)
        response_loaded = json.loads(response.data)
        assert_equals(response_loaded["item_tiids"], collection_items)

        # make a modified collection
        updated_collection_dict = {}
        updated_collection_dict["id"] = new_collection_id
        updated_collection_dict["collection_name"] = TEST_COLLECTION_NAME
        updated_collection_dict["owner"] = TEST_COLLECTION_OWNER
        updated_collection_items = collection_items
        updated_collection_items.append(["github", GITHUB_TEST_ID])
        updated_collection_dict["item_tiids"] = updated_collection_items

        # Put in a modified collection
        response = self.client.put('/collection/' + new_collection_id, 
                data=json.dumps(updated_collection_dict), 
                content_type="application/json")
        assert_equals(response.status_code, 200)  #updated
        response_loaded = json.loads(response.data)
        assert_equals(response_loaded["id"], new_collection_id)
        assert_equals(response_loaded["collection_name"], TEST_COLLECTION_NAME)
        assert_equals(response_loaded["owner"], TEST_COLLECTION_OWNER)
        assert_equals(response_loaded["item_tiids"], updated_collection_items)

        # Try to get it out again
        response = self.client.get('/collection/' + new_collection_id)
        assert_equals(response.status_code, 200)  #Created
        response_loaded = json.loads(response.data)
        assert_equals(response_loaded["id"], new_collection_id)
        assert_equals(response_loaded["item_tiids"], updated_collection_items)

        # delete collection
        collection_delete_resp = self.client.delete('/collection/' +
                new_collection_id)
        assert_equals(collection_delete_resp.status_code, 204)

        # Try to get it again, should return 404
        response = self.client.get('/collection/' + new_collection_id)
        assert_equals(response.status_code, 404)

