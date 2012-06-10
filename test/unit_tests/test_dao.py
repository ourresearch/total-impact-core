import os
import unittest, nose.tools, os
from nose.tools import nottest, raises, assert_equals, assert_true
from totalimpact import dao

TEST_DB_NAME = "test_dao"

class TestDAO(unittest.TestCase):

    def setUp(self):
        self.d = dao.Dao(os.environ["CLOUDANT_URL"], TEST_DB_NAME)

    def teardown(self):
        self.d.delete_db(TEST_DB_NAME)
        
    def test_works_at_all(self):
        assert True

    def test_create_db_uploads_views(self):
        design_doc = self.d.db.get("_design/queues")
        assert_equals(set(design_doc["views"].keys()), 
            set([u'by_alias', u'by_tiid_with_snaps', "by_type_and_id", "needs_aliases"]))

    def test_connect_db(self):
        assert self.d.db.__class__.__name__ == "Database"

    @raises(Exception) # throws ResourceConflict, which @raises doesn't catch.
    def test_create_item_fails_if_item_exists(self):
        id = "123"
        data = {}
        
        ret = self.d.create_item(data, id)
        ret = self.d.create_item(data, id)


    def test_delete(self):
        id = "123"
        
        ret = self.d.save({"id":"123"})
        assert_equals(id, ret[0])

        del_worked = self.d.delete(id)
        assert_equals(del_worked, True)
        assert_equals(self.d.get(id), None)

    def test_needs_aliases_view(self):
        res = self.d.view('queues/needs_aliases')
        nrows = len(res.rows)
        assert_equals(nrows, 0)

        self.assertTrue( isinstance(res.rows, list), res )



             
