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
