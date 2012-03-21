import os
import json
from nose.tools import assert_equal

import totalimpact.dao as dao
import totalimpact.config as config

class TestDAO:
    @classmethod
    def setup_class(cls):
        config["db_name"] = 'ti-test'
        pass

    @classmethod
    def teardown_class(cls):
        couch, db = dao.Dao.connection()
        del couch[ config["db_name"] ]

    def test_connection(self):
        pass

    def test_get_None(self):
        assert dao.Dao.get(None) == None
        
    def test_save(self):
        pass
        
    def test_query(self):
        pass
        
    def test_view(self):
        pass
        
    def test_delete(self):
        pass
        
    

