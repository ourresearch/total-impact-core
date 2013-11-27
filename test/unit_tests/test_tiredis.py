from nose.tools import raises, assert_equals, assert_items_equal, nottest
import redis
import json

from totalimpact import tiredis

SAMPLE_COLLECTION = {
    "_id": "kn5auf",
    "_rev": "8-69fdd2a34464f0ca9d02748ef057b1e8",
    "created": "2012-06-25T09:21:12.673503",
    "items": [] 
    }

class TestTiRedis():

    def setUp(self):
        # we're putting unittests for redis in their own db (number 8) so they can be deleted with abandon
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()

    def test_from_url(self):
        self.r.set("test", "foo")
        assert_equals(self.r.get("test"), "foo")

    def test_init_currently_updating_status(self):
        self.r.init_currently_updating_status("abcd", ["topsy", "wikipedia"])
        expected = {'wikipedia': '2013-11-23T23:50:58.230265: not started', 'topsy': '2013-11-23T23:50:58.230265: not started'}
        assert_items_equal(self.r.get_currently_updating("abcd"), expected.keys())
        assert_equals(": not started" in self.r.get_currently_updating("abcd")["wikipedia"], True)

    def test_set_provider_started(self):
        self.r.init_currently_updating_status("abcd", ["topsy", "wikipedia"])
        expected = {'wikipedia': '2013-11-23T23:50:58.230265: not started', 'topsy': '2013-11-23T23:50:58.230265: not started'}
        self.r.set_provider_started("abcd", "wikipedia")
        assert_equals("not started" in self.r.get_currently_updating("abcd")["wikipedia"], False)
        assert_equals(": started" in self.r.get_currently_updating("abcd")["wikipedia"], True)

    def test_set_provider_finished(self):
        assert_equals(self.r.get_num_providers_currently_updating("abcd"), 0)        
        self.r.init_currently_updating_status("abcd", ["topsy", "wikipedia"])
        assert_equals(self.r.get_num_providers_currently_updating("abcd"), 2)        
        expected = {'wikipedia': '2013-11-23T23:50:58.230265: not started', 'topsy': '2013-11-23T23:50:58.230265: not started'}
        self.r.set_provider_finished("abcd", "wikipedia")
        assert_equals(self.r.get_num_providers_currently_updating("abcd"), 1)
        assert_items_equal(self.r.get_currently_updating("abcd").keys(), ["topsy"])
        self.r.set_provider_finished("abcd", "topsy")
        assert_equals(self.r.get_num_providers_currently_updating("abcd"), 0)


    def test_memberitems_status(self):
        self.r.set_memberitems_status("abcd", 11)
        response = self.r.get_memberitems_status("abcd")
        assert_equals(response, 11)

    def test_confidence_interval_table(self):
        self.r.set_confidence_interval_table(100, 0.95, {"hi":"there"})
        response = self.r.get_confidence_interval_table(100, 0.95)
        assert_equals(response, {"hi":"there"})

    def test_reference_histogram_dict(self):
        self.r.set_reference_histogram_dict("article", "WoS", 2010, {"hi":"hist"})
        response = self.r.get_reference_histogram_dict("article", "WoS", 2010)
        assert_equals(response, {"hi":"hist"})

    def test_lookup_histogram_dict(self):
        self.r.set_reference_lookup_dict("article", "WoS", 2010, {"hi":"lookup"})
        response = self.r.get_reference_lookup_dict("article", "WoS", 2010)
        assert_equals(response, {"hi":"lookup"})


