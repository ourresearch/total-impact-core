import json, os, Queue, datetime, copy

from totalimpact import app, db
from totalimpact import tiredis
from totalimpact import updater
from totalimpact import item as item_module
from nose.tools import raises, assert_items_equal, assert_equals, assert_greater, nottest
from test.utils import slow
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

from totalimpact import REDIS_UNITTEST_DATABASE_NUMBER


class TestUpdater():
    def setUp(self):

        self.db = setup_postgres_for_unittests(db, app)

        # do the same thing for the redis db, set up the test redis database.  We're using DB Number 8
        self.r = tiredis.from_url("redis://localhost:6379", db=REDIS_UNITTEST_DATABASE_NUMBER)
        self.r.flushdb()
        now = datetime.datetime.utcnow()
        self.before = now - datetime.timedelta(days=2)
        self.last_week = now - datetime.timedelta(days=7)
        self.last_year = now - datetime.timedelta(days=370)

        # save basic item beforehand, and some additional items
        self.fake_item_doc = {
            "_id": "tiid1",
            "type": "item",
            "last_modified": now.isoformat(),
            "last_update_run": now.isoformat(),
            "aliases":{"doi":["10.7554/elife.1"]},
            "biblio": {"year":"2012"},
            "metrics": {}
        }
        self.fake_item_obj = item_module.create_objects_from_item_doc(self.fake_item_doc)        
        self.db.session.add(self.fake_item_obj)

        another_elife = copy.copy(self.fake_item_doc)
        another_elife["_id"] = "tiid2"
        another_elife["aliases"] = {"doi":["10.7554/ELIFE.2"]}
        another_elife["last_modified"] = self.before.isoformat()
        another_elife["last_update_run"] = self.before.isoformat()
        another_elife_obj = item_module.create_objects_from_item_doc(another_elife)        
        self.db.session.add(another_elife_obj)

        different_journal = copy.copy(self.fake_item_doc)
        different_journal["_id"] = "tiid3"
        different_journal["aliases"] = {"doi":["10.3897/zookeys.3"], "biblio":[{"year":1999}]}
        different_journal["last_modified"] = now.isoformat()
        different_journal["last_update_run"] = self.last_week.isoformat()
        different_journal_obj = item_module.create_objects_from_item_doc(different_journal)        
        self.db.session.add(different_journal_obj)

        different_journal2 = copy.copy(different_journal)
        different_journal2["_id"] = "tiid4"
        different_journal2["last_update_run"] = self.last_year.isoformat()
        different_journal_obj2 = item_module.create_objects_from_item_doc(different_journal2)        
        self.db.session.add(different_journal_obj2)

        self.db.session.commit()


    def tearDown(self):
        teardown_postgres_for_unittests(self.db)

    def test_get_tiids_not_updated_since(self):
        number_to_update = 10
        schedule = {"max_days_since_created": 7, "max_days_since_updated": 1, "exclude_old": True}      
        tiids = updater.get_tiids_not_updated_since(schedule, number_to_update)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid2']))

        schedule = {"max_days_since_created": 7, "max_days_since_updated": 1, "exclude_old": False}      
        tiids = updater.get_tiids_not_updated_since(schedule, number_to_update)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid2', 'tiid3', 'tiid4']))


    def test_gold_update(self):
        number_to_update = 10        
        tiids = updater.gold_update(number_to_update, self.r)
        print tiids
        assert_equals(sorted(tiids), sorted(['tiid2', 'tiid4']))


    def test_gold_update_sets_last_update_run(self):
        number_to_update = 10        
        now = datetime.datetime.utcnow().isoformat()
        tiids = updater.gold_update(number_to_update, self.r)
        item_obj = item_module.Item.query.get(tiids[0])  # can use this method because don't need metrics
        print now
        print item_obj.last_update_run

        assert_greater(item_obj.last_update_run.isoformat(), now)

