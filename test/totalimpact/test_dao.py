import unittest
from nose.tools import raises

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
    def test_01_get_None(self):
        assert dao.Dao.get('woeifwoifmwiemwfw9m09m49ufm9fu93u4f093u394umf093u4mf') == None
        
    def test_02_save(self):
        assert self.d.id == None
        self.d.save()
        assert self.d.id != None
        assert self.d.version != None
        assert self.d.get(self.d.id) != None
        
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

