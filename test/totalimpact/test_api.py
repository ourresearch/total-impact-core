import unittest, json, uuid
from nose.tools import nottest, assert_equals

from totalimpact import api
from totalimpact.providers.dryad import Dryad


TEST_DRYAD_DOI = "10.5061/dryad.7898"
GOLD_MEMBER_ITEM_CONTENT = ["MEMBERITEM CONTENT"]

def MOCK_member_items(self, a, b):
    return(GOLD_MEMBER_ITEM_CONTENT)


class TestWeb(unittest.TestCase):

    def setUp(self):
        self.app = api.app.test_client()

        # Mock out relevant methods of the Dryad provider
        self.orig_Dryad_member_items = Dryad.member_items
        Dryad.member_items = MOCK_member_items

    def tearDown(self):
        Dryad.member_items = self.orig_Dryad_member_items


    def test_memberitems_get(self):
        response = self.app.get('/provider/Dryad/memberitems?query=Otto%2C%20Sarah%20P.&type=author')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data), GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")

    def test_tiid_post(self):
        # POST isn't supported
        response = self.app.post('/tiid/Dryad/NotARealId')
        assert_equals(response.status_code, 405)  # Method Not Allowed


    def test_item_get_unknown_tiid(self):
        # pick a random ID, very unlikely to already be something with this ID
        response = self.app.get('/item/' + str(uuid.uuid4()))
        assert_equals(response.status_code, 404)  # Not Found


    def test_item_post_unknown_provider(self):
        response = self.app.post('/item/AnUnknownProviderName/AnIdOfSomeKind/')
        assert_equals(response.status_code, 501)  # "Not implemented"

    def test_item_post_unknown_tiid(self):
        response = self.app.post('/item/Dryad/AnIdOfSomeKind/')
        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(len(json.loads(response.data)), 32)
        assert_equals(response.mimetype, "application/json")

    def test_item_post_known_tiid(self):
        response = self.app.post('/item/Dryad/IdThatAlreadyExists/')
        print response
        print response.data

        # FIXME should check and if already exists return 200        
        # right now this makes a new item every time, creating many dups
        assert_equals(response.status_code, 201) 
        assert_equals(len(json.loads(response.data)), 32)
        assert_equals(response.mimetype, "application/json")

    def test_item_get_success(self):
        # First put something in
        response_create = self.app.post('/item/Dryad/AnIdOfSomeKind/')
        tiid = response_create.data

        # Now try to get it out
        # Strip off leading and trailing quotation marks
        tiid = tiid.replace('"', '')
        response = self.app.get('/item/' + tiid)
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data).keys(), [u'created', u'last_requested', u'metrics', u'last_modified', u'biblio', u'id', u'aliases'])
        assert_equals(response.mimetype, "application/json")


