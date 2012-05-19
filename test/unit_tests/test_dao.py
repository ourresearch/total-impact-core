import unittest
import nose.tools
from nose.tools import nottest, raises, assert_equals, assert_true

from totalimpact import dao
# To read global config
from totalimpact.api import app

TEST_DB_NAME = "test_dao"


class TestDAO(unittest.TestCase):

    def setUp(self):
        self.d = dao.Dao(TEST_DB_NAME, app.config["DB_URL"], 
            app.config["DB_USERNAME"], app.config["DB_PASSWORD"])
        if self.d.db_exists(TEST_DB_NAME):
            self.d.delete_db(TEST_DB_NAME)
        
    def test_create_db(self):
        self.d.create_db(TEST_DB_NAME)
        assert self.d.db.__class__.__name__ == "Database"

    def test_create_db_uploads_views(self):
        self.d.create_db(TEST_DB_NAME)
        design_doc = self.d.db.get("_design/queues")
        assert_equals(set(design_doc["views"].keys()), 
            set([u'requested', u'by_alias']))

    def test_db_exists(self):
        self.d.create_db(TEST_DB_NAME)
        assert self.d.db_exists("unlikely_name") == False
        assert self.d.db_exists(TEST_DB_NAME) == True

    def test_connect_db(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        assert self.d.db.__class__.__name__ == "Database"
        assert_equals(TEST_DB_NAME, self.d.db_name)

    @raises(LookupError)
    def test_connect_db_exception(self):
        self.d.connect_db("nonexistant_database")


    @raises(Exception) # throws ResourceConflict, which @raises doesn't catch.
    def test_create_item_fails_if_item_exists(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"
        data = {}
        
        ret = self.d.create_item(data, id)
        ret = self.d.create_item(data, id)

    def test_delete(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"
        
        ret = self.d.save({"id":"123"})
        assert_equals(id, ret[0])

        del_worked = self.d.delete(id)
        assert_equals(del_worked, True)
        assert_equals(self.d.get(id), None)

    def test_create_new_db_and_connect(self):
       self.d.create_db(TEST_DB_NAME)
       self.d.connect_db(TEST_DB_NAME)
       assert_equals(self.d.db_exists(TEST_DB_NAME), True)


    def test_query(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
  
        map_fun = 'function(doc) { emit(doc, null); }'
        res = self.d.query(map_fun=map_fun)
        self.assertTrue( isinstance(res.rows,list), res )
        
    def test_view_all_docs(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        res = self.d.view('_all_docs')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )

    @raises(LookupError)    
    def test_view_queues_noSuchView(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        res = self.d.view('queues/noSuchView')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )   




             
