import unittest
import nose.tools
from nose.tools import nottest, raises, assert_equals

from totalimpact import dao, config

class TestDAO(unittest.TestCase):

    def setUp(self):
        conf = config.Configuration()
        self.d = dao.Dao(conf)
        if self.d.db_exists("test"):
            self.d.delete_db("test")
        
    def test_create_db(self):
        self.d.create_db("test")
        assert self.d.db.__class__.__name__ == "Database"

    def test_db_exists(self):
        self.d.create_db("test")
        assert self.d.db_exists("unlikely_name") == False
        assert self.d.db_exists("test") == True

    def test_connect(self):
        self.d.create_db("test")
        self.d.connect("test")
        assert self.d.db.__class__.__name__ == "Database"

    @raises(LookupError)
    def test_connect_exception(self):
        self.d.connect("nonexistant_database")

    '''
    def test_save_section_and_get(self):
        self.d.create_db("test")
        self.d.connect("test")

        metrics = {"metrics":{"mendeley1": {}, "wikipedia1":{}}}
        ret = self.d.save_section(metrics, "metrics")
        
        assert len(ret) == 2, ret
        
        id = ret[0]
        doc = self.d.get(id)
        assert_equals(doc["metrics"], metrics)
   ''' 

    def test_create_and_get_item(self):
        self.d.create_db("test")
        self.d.connect("test")
        
        ret = self.d.create_item()
        assert_equals(2, len(ret))
        doc = self.d.get(ret[0])
        assert_equals(ret[0], doc["_id"])
        assert_equals(0, doc["last_modified"])



        '''
    def test_03_query(self):
        map_fun = 'function(doc) { emit(doc, null); }'
        res = self.d.query(map_fun=map_fun)
        self.assertTrue( isinstance(res.rows,list), res )
        
    def test_04_view(self):
        res = self.d.view('_all_docs')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )
        
    def test_05_delete(self):
        theid = self.d.id
        self.d.delete()
        assert self.d.get(theid) == None
    '''

