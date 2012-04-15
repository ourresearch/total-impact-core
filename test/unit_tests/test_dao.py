import unittest
import nose.tools
from nose.tools import nottest, raises, assert_equals, assert_true

from totalimpact import dao

TEST_DB_NAME = "test_dao"

class TestDAO(unittest.TestCase):

    def setUp(self):
        self.d = dao.Dao(TEST_DB_NAME)
        if self.d.db_exists(TEST_DB_NAME):
            self.d.delete_db(TEST_DB_NAME)
        
    def test_create_db(self):
        self.d.create_db(TEST_DB_NAME)
        assert self.d.db.__class__.__name__ == "Database"

    def test_create_db_uploads_views(self):
        self.d.create_db(TEST_DB_NAME)
        design_doc = self.d.db.get("_design/queues")
        assert_equals(set(design_doc["views"].keys()), 
            set([u'metrics', u'by_alias', u'aliases']))

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

    def test_create_item(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"

        data = {"aliases": {}, "biblio": {}, "metrics":{}}
        ret = self.d.create_item(data, id)
        assert_equals(ret[0], id)

        doc = self.d.get(id)
        assert_true(("aliases" in doc) and ("biblio" in doc) and ("metrics" in doc))
        assert_equals(0, doc["last_modified"])
        assert 10 == len(str(int(doc["created"]))), int(doc["created"])

    @raises(Exception) # throws ResourceConflict, which @raises doesn't catch.
    def test_create_item_fails_if_item_exists(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"
        data = {}
        
        ret = self.d.create_item(data, id)
        ret = self.d.create_item(data, id)

    def test_update_items_updates(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"

        # create a new doc
        data = {"aliases": {"one": "uno", "two": "dos"}, "biblio": {}, "metrics":{}}
        ret = self.d.create_item(data, id)
        assert_equals(id, ret[0])

        # update it and see what we did
        data["aliases"] = {"one": "uno", "two": "dos", "three": "tres"}
        ret = self.d.update_item(data, id)
        doc = self.d.get(id)
        assert_equals(doc["aliases"], data["aliases"])

    def test_update_items_adds_items_to_sections_instead_of_overwriting(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"

        # create a new doc
        data = {"aliases": {"one": "uno", "two": "dos"}, "biblio": {}, "metrics":{}}
        ret = self.d.create_item(data, id)
        assert_equals(id, ret[0])

        # update it and see what we did
        data["aliases"] = {"three": "tres"}
        ret = self.d.update_item(data, id)
        doc = self.d.get(id)
        assert_equals(doc["aliases"], {"one":"uno", "two":"dos", "three":"tres"})

    def test_delete(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        id = "123"
        
        ret = self.d.create_item({}, id)
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


    def test_view_queues_aliases(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        res = self.d.view('queues/aliases')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )

    def test_view_queues_metrics(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        res = self.d.view('queues/metrics')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )

    @raises(LookupError)    
    def test_view_queues_noSuchView(self):
        self.d.create_db(TEST_DB_NAME)
        self.d.connect_db(TEST_DB_NAME)
        res = self.d.view('queues/noSuchView')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )   




             
