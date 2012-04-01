import unittest, json
from nose.tools import nottest

from totalimpact import api

class TestWeb(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass

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


