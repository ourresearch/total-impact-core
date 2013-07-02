import json, os, Queue, datetime, copy

from totalimpact import dao, tiredis
from totalimpact import updater
from totalimpact import item
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
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        last_week = now - datetime.timedelta(days=7)

        # save basic item beforehand, and some additional items
        self.fake_item = {
            "_id": "tiid1",
            "type": "item",
            "last_modified": now.isoformat(),
            "aliases":{"doi":["10.7554/elife.1"]},
            "biblio": {"year":"2012"},
            "metrics": {}
        }
        self.d.save(self.fake_item)

        another_elife = copy.copy(self.fake_item)
        another_elife["_id"] = "tiid2"
        another_elife["aliases"] = {"doi":["10.7554/ELIFE.2"]}
        another_elife["last_modified"] = yesterday.isoformat()
        self.d.save(another_elife)

        different_journal = copy.copy(self.fake_item)
        different_journal["_id"] = "tiid3"
        different_journal["aliases"] = {"doi":["10.3897/zookeys.3"]}
        different_journal["last_modified"] = now.isoformat()
        different_journal["last_update_run"] = last_week.isoformat()
        self.d.save(different_journal)

    def teardown(self):
        self.d.delete_db(os.environ["CLOUDANT_DB"])
        self.r.flushdb()

    def test_get_matching_dois_in_db(self):
        dois = updater.get_matching_dois_in_db("10.7554/elife.", self.d)
        print dois
        assert_equals(dois, ['10.7554/elife.1', '10.7554/ELIFE.2'])

    def test_get_matching_dois_in_db(self):
        (tiids, docs) = updater.get_matching_dois_in_db(2003, "10.7554/elife", self.d)
        print tiids
        assert_equals(tiids, [])
        (tiids, docs) = updater.get_matching_dois_in_db(2003, "10.3897/zookeys", self.d)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid3']))

    def test_update_active_publisher_items(self):
        number_to_update = 10        
        tiids = updater.update_active_publisher_items(number_to_update, None, self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid3']))

    def test_update_active_publisher_items_single_publisher(self):
        number_to_update = 10        
        tiids = updater.update_active_publisher_items(number_to_update, "elife", self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), [])

        tiids = updater.update_active_publisher_items(number_to_update, "pensoft", self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), ['tiid3'])

    def test_get_least_recently_updated_tiids_in_db(self):
        number_to_update = 2
        (tiids_to_update, docs) = updater.get_least_recently_updated_tiids_in_db(number_to_update, self.d)
        print tiids_to_update
        assert_equals(sorted(tiids_to_update), sorted(['tiid2', 'tiid3']))

    def test_update_docs_with_updater_timestamp(self):
        (tiids_to_update, docs) = updater.get_least_recently_updated_tiids_in_db(2, self.d)
        response = updater.update_docs_with_updater_timestamp(docs, self.d)
        assert_equals(response[0][0], True)
        assert_equals(response[0][1], 'tiid3')
        assert_equals(self.d.get(tiids_to_update[0]).keys(), ['_rev', 'metrics', 'last_modified', 'biblio', '_id', 'type', 'last_update_run', 'aliases'])

    def test_gold_update(self):
        number_to_update = 10        
        tiids = updater.gold_update(number_to_update, self.r, self.d)
        print tiids
        assert_equals(sorted(tiids), sorted([]))


