import unittest, json
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


    # FIXME: this test is breaking
    @nottest
    def test_item(self):
        res = self.app.get('/item/' + self.TESTITEM)
        assert res.status == '200 OK', res.status
        item = json.loads(res.data)
        assert item['_id'] == self.TESTITEM, item
        
    def test_item_id(self):
        pass
        
    # FIXME: this test is breaking
    @nottest        
    def test_items(self):
        res = self.app.get('/items/' + self.TESTITEM + ',' + self.TESTITEM2)
        assert res.status == '200 OK', res.status
        item = json.loads(res.data)
        assert item[0]['_id'] == self.TESTITEM, item
        assert item[1]['_id'] == self.TESTITEM2, item
        
    def test_provider_memberitems(self):
        pass

    def test_provider_aliases(self):
        pass
        
    def test_collection(self):
        pass

    def test_user(self):
        pass


