import os
import json
from nose.tools import assert_equal

from totalimpact.config import Configuration

class TestDAO:
    @classmethod
    def setup_class(cls):
        pass
        
    @classmethod
    def teardown_class(cls):
        pass
        
    def test_connection(self):
        pass

    def test_get_None(self):
        assert dao.Dao.get(None) == None
        
    def test_save(self):
        obj = dao.Dao()
        assert obj.id == None
        obj.save()
        assert obj.id != None
        assert obj.version != None
        
    def test_query(self):
        dbobj = dao.Dao()
        map_fun = 'function(doc) { emit(doc, null); }'
        res = dbobj.query(map_fun)
        assert isinstance(res,list)
        
    def test_view(self):
        docs = dao.Dao().view('_all_docs')
        assert isinstance(docs,list)
        
    def test_delete(self):
        obj = dao.Dao()
        obj.save()
        assert obj.id != None
        theid = obj.id
        assert obj.delete()
        assert dao.Dao.get(theid) == None
    

