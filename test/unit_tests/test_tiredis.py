from nose.tools import raises, assert_equals, nottest
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
        self.r = tiredis.from_url("redis://localhost:6379")
        self.r.flushdb()


    def test_from_url(self):
        self.r.set("test", "foo")
        assert_equals(self.r.get("test"), "foo")

    def test_set_num_providers_left(self):
        self.r.set_num_providers_left("abcd", 11)
        assert_equals("11", self.r.get("abcd"))

    def test_get_num_providers_left(self):
        self.r.set_num_providers_left("abcd", 11)
        num_left = self.r.get_num_providers_left("abcd")
        assert_equals(11, num_left)

    def test_get_num_providers_left_is_none(self):
        num_left = self.r.get_num_providers_left("notinthedatabase")
        assert_equals(None, num_left)


    def test_decr_num_providers_left(self):
        self.r.set_num_providers_left("abcd", 11)
        assert_equals("11", self.r.get("abcd"))

        self.r.decr_num_providers_left("abcd", "myprovider")
        assert_equals("10", self.r.get("abcd"))

    def test_cache_collection(self):
        success = self.r.cache_collection(SAMPLE_COLLECTION)
        assert_equals(success, True)
        stored_doc = self.r.get("cid:kn5auf")
        assert_equals(stored_doc, json.dumps(SAMPLE_COLLECTION))

    def test_get_collection(self):
        self.r.cache_collection(SAMPLE_COLLECTION)
        stored_doc = self.r.get_collection("kn5auf")
        assert_equals(stored_doc, SAMPLE_COLLECTION)

    def test_get_collection_that_is_not_there(self):
        stored_doc = self.r.get_collection("kn5auf")
        assert_equals(stored_doc, None)

    def test_expire_collection(self):
        self.r.cache_collection(SAMPLE_COLLECTION)

        # check it is there
        stored_doc = self.r.get("cid:kn5auf")
        assert_equals(stored_doc, json.dumps(SAMPLE_COLLECTION))

        # now expire it
        success = self.r.expire_collection("kn5auf")
        assert_equals(success, True)

        # now check it is gone
        stored_doc = self.r.get("cid:kn5auf")
        assert_equals(stored_doc, None)

    def test_expire_collection_that_is_not_there(self):
        success = self.r.expire_collection("abcdef")
        assert_equals(success, True)



