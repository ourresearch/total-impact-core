from nose.tools import raises, assert_equals, nottest
import redis
from totalimpact import tiredis


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

