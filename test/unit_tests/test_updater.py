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
            "aliases":{"doi":["10.7554/elife.1"]},
            "biblio": {},
            "metrics": {}
        }
        self.d.save(self.fake_item)

        another_elife = copy.copy(self.fake_item)
        another_elife["_id"] = "tiid2"
        another_elife["aliases"] = {"doi":["10.7554/eLife.2"]}
        self.d.save(another_elife)

        different_journal = copy.copy(self.fake_item)
        different_journal["_id"] = "tiid3"
        different_journal["aliases"] = {"doi":["10.7554/anotherjournal.2"]}
        self.d.save(different_journal)

    def teardown(self):
        self.d.delete_db(os.environ["CLOUDANT_DB"])
        self.r.flushdb()

    def test_show_elife_ids(self):
        dois = updater.get_elife_dois(self.d)
        print dois
        assert_equals(dois, ['10.7554/elife.1', '10.7554/eLife.2'])

    def test_create_and_update_elife_dois(self):
        tiids = updater.update_elife_dois(self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid1', 'tiid2']))


