import unittest

from totalimpact import dao

class TestDAO(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.TESTDB = 'ti_test'
        cls.d = dao.Dao()
        cls.d.config.db_name = cls.TESTDB
        cls.couch, cls.db = cls.d.connection()

    @classmethod
    def teardown_class(cls):
        cls.couch.delete( cls.TESTDB )
        
    def test_01_get_None(self):
        assert self.d.get(None) == None
        
    def test_02_save(self):
        assert self.d.id == None
        self.d.save()
        assert self.d.id != None
        assert self.d.version != None
        
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
    

