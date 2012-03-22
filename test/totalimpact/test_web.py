import os
import json
from nose.tools import assert_equal

from totalimpact import web
import totalimpact.config as config

class TestWeb:
    @classmethod
    def setup_class(cls):
        config["db_name"] = 'ti-test'
        cls.app = web.app.test_client()

    @classmethod
    def teardown_class(cls):
        couch, db = dao.Dao.connection()
        del couch[ config["db_name"] ]

    def test_root(self):
        res = self.app.get('/')
        assert 'Total Impact' in res.data, res.data

    def test_about(self):
        res = self.app.get('/about')
        assert 'Total Impact' in res.data, res.data

    def test_item(self):
        pass
        
    def test_item_id(self):
        pass
        
    def test_items(self):
        pass
        
    def test_provider_memberitems(self):
        pass

    def test_provider_aliases(self):
        pass
        
    def test_collection(self):
        pass

    def test_user(self):
        pass


