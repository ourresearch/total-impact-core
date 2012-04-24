import os, unittest, time, json
from nose.tools import nottest, assert_equals
from urllib import quote_plus

from totalimpact import dao, api

PLOS_TEST_DOI = "10.1371/journal.pone.0004803"

class TestTiidRetrieve(unittest.TestCase):

    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True 
        self.client = self.app.test_client()

        # setup the database
        self.testing_db_name = "tiid_retrieve_test"
        self.old_db_name = self.app.config["DB_NAME"]
        self.app.config["DB_NAME"] = self.testing_db_name
        self.d = dao.Dao(self.testing_db_name, self.app.config["DB_URL"],
            self.app.config["DB_USERNAME"], self.app.config["DB_PASSWORD"])


    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name


    def test_tiid_retrieve(self):
        self.d.create_new_db_and_connect(self.testing_db_name)

        # try to retrieve tiid id for something that doesn't exist yet
        plos_no_tiid_resp = self.client.get('/tiid/doi/' + 
                quote_plus(PLOS_TEST_DOI))
        assert_equals(plos_no_tiid_resp.status_code, 404)  # Not Found

        # create new plos item from a doi
        plos_create_tiid_resp = self.client.post('/item/doi/' + 
                quote_plus(PLOS_TEST_DOI))
        plos_create_tiid = json.loads(plos_create_tiid_resp.data)

        # retrieve the plos tiid using tiid api
        plos_lookup_tiid_resp = self.client.get('/tiid/doi/' + 
                quote_plus(PLOS_TEST_DOI))
        plos_lookup_tiids = json.loads(plos_lookup_tiid_resp.data)

        # check that the tiids are the same
        assert_equals(plos_create_tiid, plos_lookup_tiids[0])


