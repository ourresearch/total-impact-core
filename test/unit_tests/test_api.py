import unittest, json, uuid
from nose.tools import nottest, assert_equals

from totalimpact import api, dao
from totalimpact.config import Configuration
from totalimpact.providers.dryad import Dryad
from totalimpact.core import app


TEST_DRYAD_DOI = "10.5061/dryad.7898"
GOLD_MEMBER_ITEM_CONTENT = ["MEMBERITEM CONTENT"]

def MOCK_member_items(self, a, b):
    return(GOLD_MEMBER_ITEM_CONTENT)


class TestWeb(unittest.TestCase):

    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True
        self.client = self.app.test_client()
        
        # setup the database
        self.testing_db_name = "api_test"
        self.old_db_name = self.app.config["DB_NAME"]
        self.app.config["DB_NAME"] = self.testing_db_name
        self.d = dao.Dao(self.app.config["DB_NAME"])

        self.d.create_new_db_and_connect(self.testing_db_name)
        
        # Mock out relevant methods of the Dryad provider
        self.orig_Dryad_member_items = Dryad.member_items
        Dryad.member_items = MOCK_member_items

        
    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name
        
        Dryad.member_items = self.orig_Dryad_member_items


    def test_memberitems_get(self):
        response = self.client.get('/provider/dryad/memberitems?query=Otto%2C%20Sarah%20P.&type=author')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data), GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")

    def test_tiid_post(self):
        # POST isn't supported
        response = self.client.post('/tiid/Dryad/NotARealId')
        assert_equals(response.status_code, 405)  # Method Not Allowed


    def test_item_get_unknown_tiid(self):
        # pick a random ID, very unlikely to already be something with this ID
        response = self.client.get('/item/' + str(uuid.uuid4()))
        assert_equals(response.status_code, 404)  # Not Found


    def test_item_post_unknown_namespace(self):
        response = self.client.post('/item/AnUnknownNamespace/AnIdOfSomeKind/')
        assert_equals(response.status_code, 501)  # "Not implemented"

    def test_item_post_unknown_tiid(self):
        response = self.client.post('/item/doi/AnIdOfSomeKind/')
        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(len(json.loads(response.data)), 32)
        assert_equals(response.mimetype, "application/json")

    def test_item_post_known_tiid(self):
        response = self.client.post('/item/doi/IdThatAlreadyExists/')
        print response
        print response.data

        # FIXME should check and if already exists return 200        
        # right now this makes a new item every time, creating many dups
        assert_equals(response.status_code, 201) 
        assert_equals(len(json.loads(response.data)), 32)
        assert_equals(response.mimetype, "application/json")

    def test_item_get_success_fakeid(self):
        # First put something in
        response_create = self.client.post('/item/doi/AnIdOfSomeKind/')
        tiid = response_create.data

        # Now try to get it out
        # Strip off leading and trailing quotation marks
        tiid = tiid.replace('"', '')
        response = self.client.get('/item/' + tiid)
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(
            set(json.loads(response.data).keys()),
            set([u'aliases', u'biblio', u'created', u'id', u'last_modified', u'last_requested', u'metrics'])
            )
        assert_equals(response.mimetype, "application/json")

    def test_item_get_success_realid(self):
        # First put something in
        response = self.client.get('/item/doi/' + TEST_DRYAD_DOI.replace("/", "%2F")) 
        tiid = response.data
        print response
        print tiid 

    def test_item_post_urldecodes(self):
        resp = self.client.post('/item/doi/' + TEST_DRYAD_DOI.replace("/", "%2F"))
        tiid = resp.data.replace('"', '')

        resp = self.client.get('/item/' + tiid)
        saved_item = json.loads(resp.data) 

        assert_equals(TEST_DRYAD_DOI, saved_item["aliases"]["doi"])


