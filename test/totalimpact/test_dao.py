import unittest
import nose.tools
from nose.tools import nottest, raises, assert_equals, assert_true

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

    def test_create_item(self):
        self.d.create_db("test")
        self.d.connect("test")
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
        self.d.create_db("test")
        self.d.connect("test")
        id = "123"
        data = {}
        
        ret = self.d.create_item(data, id)
        ret = self.d.create_item(data, id)

    def test_update_items_updates(self):
        self.d.create_db("test")
        self.d.connect("test")
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
        self.d.create_db("test")
        self.d.connect("test")
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
        self.d.create_db("test")
        self.d.connect("test")
        id = "123"
        
        ret = self.d.create_item({}, id)
        assert_equals(id, ret[0])

        del_worked = self.d.delete(id)
        assert_equals(del_worked, True)
        assert_equals(self.d.get(id), None)

        


        '''
    def test_03_query(self):
        map_fun = 'function(doc) { emit(doc, null); }'
        res = self.d.query(map_fun=map_fun)
        self.assertTrue( isinstance(res.rows,list), res )
        
    def test_04_view(self):
        res = self.d.view('_all_docs')
        print res
        self.assertTrue( isinstance(res['rows'],list), res )

    '''

