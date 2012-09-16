import os
import unittest, nose.tools, os
from nose.tools import nottest, raises, assert_equals, assert_true
from totalimpact import dao

TEST_DB_NAME = "test_dao"


class TestDbUrl(unittest.TestCase):
    
    def setUp(self):
        url = "https://mah_username:mah_password@mah_username.cloudant.com"
        self.db_url = dao.DbUrl(url)
        pass
    
    def test_get_username(self):
        username = self.db_url.get_username()
        assert_equals(
            username,
            "mah_username"
        )
    def test_get_password(self):
        password = self.db_url.get_password()
        assert_equals(
            password,
            "mah_password"
        )
    def test_get_base(self):
        base = self.db_url.get_base()
        assert_equals(
            base,
            "https://mah_username.cloudant.com"
        )
        

class TestDAO(unittest.TestCase):

    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.d.update_design_doc()

    def teardown(self):
        pass

    def test_create_db_uploads_views(self):
        design_doc = self.d.db.get("_design/queues")
        assert_equals(set(design_doc["views"].keys()),
            set([u'by_alias', "by_type_and_id", "latest-collections", "reference-sets"]))

        design_doc = self.d.db.get("_design/collections_with_items")
        assert_equals(set(design_doc["views"].keys()),
            set([u"collections_with_items"]))

    def test_connect_db(self):
        assert self.d.db.__class__.__name__ == "Database"

    def test_delete(self):
        id = "123"

        ret = self.d.save({"_id":"123"})
        assert_equals(id, ret[0])

        del_worked = self.d.delete(id)
        assert_equals(del_worked, True)
        assert_equals(self.d.get(id), None)



             
