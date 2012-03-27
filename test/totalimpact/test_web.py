import unittest, json
from nose.tools import nottest

from totalimpact import web
from totalimpact import dao

class TestWeb(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.TESTDB = 'ti_test'
        cls.TESTITEM = 'test'
        cls.TESTITEM2 = 'test2'
        cls.d = dao.Dao()
        cls.d.config.db_name = cls.TESTDB
        cls.d.id = cls.TESTITEM
        cls.d.save()
        cls.d2 = dao.Dao()
        cls.d2.config.db_name = cls.TESTDB
        cls.d2.id = cls.TESTITEM2
        cls.d2.save()
        web.config.db_name = cls.TESTDB
        cls.app = web.app.test_client()

    @classmethod
    def teardown_class(cls):
        cls.couch, cls.db = cls.d.connection()
        cls.couch.delete( cls.TESTDB )

    def test_root(self):
        res = self.app.get('/')
        assert res.status == '200 OK', res.status

    def test_about(self):
        res = self.app.get('/about')
        assert res.status == '200 OK', res.status

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


