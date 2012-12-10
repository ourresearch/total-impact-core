import json, os, Queue, datetime, copy

from totalimpact import dao, tiredis
from totalimpact import updater
from totalimpact.models import ItemFactory
from nose.tools import raises, assert_equals, nottest
from test.utils import slow

class TestUpdater():
    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        # need views to make sure to create them
        self.d.update_design_doc()

        # do the same thing for the redis db, set up the test redis database.  We're using DB Number 8
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()

        # save basic item beforehand, and some additional items
        self.fake_item = {
            "_id": "tiid1",
            "type": "item",
            "last_modified": "2012-12-08T23:56:06.004925",
            "aliases":{"doi":["10.7554/elife.1"]},
            "biblio": {},
            "metrics": {}
        }
        self.d.save(self.fake_item)

        another_elife = copy.copy(self.fake_item)
        another_elife["_id"] = "tiid2"
        another_elife["aliases"] = {"doi":["10.7554/ELIFE.2"]}
        another_elife["last_modified"] = "2010-01-01T23:56:06.004925",
        self.d.save(another_elife)

        different_journal = copy.copy(self.fake_item)
        different_journal["_id"] = "tiid3"
        different_journal["aliases"] = {"doi":["10.3897/zookeys.3"]}
        different_journal["last_modified"] = "2011-10-01T23:56:06.004925",
        self.d.save(different_journal)

    def teardown(self):
        self.d.delete_db(os.environ["CLOUDANT_DB"])
        self.r.flushdb()

    def test_get_matching_dois_in_db(self):
        dois = updater.get_matching_dois_in_db("10.7554/elife.", self.d)
        print dois
        assert_equals(dois, ['10.7554/elife.1', '10.7554/ELIFE.2'])

    def test_update_dois_from_doi_prefix(self):
        tiids = updater.update_dois_from_doi_prefix("10.7554/elife.", self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid1', 'tiid2']))

    def test_update_active_publisher_items(self):
        tiids = updater.update_active_publisher_items(self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid2', 'tiid1', 'tiid3']))

    def test_get_least_recently_updated_tiids_in_db(self):
        tiids = updater.get_least_recently_updated_tiids_in_db(2, self.d)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid3', 'tiid2']))
