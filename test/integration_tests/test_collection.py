import os, unittest, time, json
from nose.tools import nottest, assert_equals

from totalimpact.config import Configuration
from totalimpact.util import slow
from totalimpact import dao, api
from totalimpact.tilogging import logging

PLOS_TEST_DOI = "10.1371/journal.pone.0004803"
DRYAD_TEST_DOI = "10.5061/dryad.7898"
GITHUB_TEST_ID = "homebrew"

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
        self.config = Configuration()
        self.d = dao.Dao(self.config)


    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name

    @nottest
    def test_collection(self):
        self.d.create_new_db_and_connect(self.testing_db_name)

        collection_items = []
        collection_items.append(["doi", PLOS_TEST_DOI.replace("/", "%2F")])
        collection_items.append(["doi", DRYAD_TEST_DOI.replace("/", "%2F")])

        # create new collection
        collection_create_resp = self.client.post('/collection/' + PLOS_TEST_DOI.replace("/", "%2F"), collection_items)
        collection_id = collection_create_resp.data

        # check new collection
        collection_get_resp = self.client.get('/collection/' + collection_id)
        collection_resp_dict = json.loads(collection_get_resp.data)
        assert_equals(collection_resp_dict["id"], collection_id)
        assert_equals(collection_resp_dict["item_ids"], collection_items)
        assert_equals(collection_resp_dict["collection_name"], "")
        assert_equals(collection_resp_dict["owner"], "")

        # update collection with another item and metadata
        updated_collection_items = collection_items
        updated_collection_items.append(["github", GITHUB_TEST_ID])

        updated_collection_dict = collection_resp_dict
        updated_collection_dict["item_ids"] = updated_collection_items
        updated_collection_dict["collection_name"] = "My Collection"
        updated_collection_dict["owner"] = "abcdef"

        collection_put_resp = self.client.put('/collection/' + collection_id, collection_resp_dict)
        resp_dict = json.loads(collection_put_resp.data)
        assert_equals(collection_resp_dict["id"], collection_id)
        assert_equals(collection_resp_dict["item_ids"], updated_collection_items)
        assert_equals(collection_resp_dict["collection_name"], "My Collection")
        assert_equals(collection_resp_dict["owner"], "abcdef")

        # delete collection
        collection_delete_resp = self.client.delete('/collection/' + collection_id)
        asserte_equals(collection_delete_resp.status_code, 200)

