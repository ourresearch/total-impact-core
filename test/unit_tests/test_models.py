from nose.tools import raises, assert_equals, nottest
import os, unittest, hashlib, json, pprint, datetime
from time import sleep
from werkzeug.security import generate_password_hash
from totalimpact import models, tiredis
from totalimpact.providers import bibtex, github
from totalimpact import REDIS_UNITTEST_DATABASE_NUMBER


class TestMemberItems():

    def setUp(self):
        # setup a clean new redis database at our unittest redis DB location: Number 8
        self.r = tiredis.from_url("redis://localhost:6379", db=REDIS_UNITTEST_DATABASE_NUMBER)
        self.r.flushdb()

        bibtex.Bibtex.paginate = lambda self, x: {"pages": [1,2,3,4], "number_entries":10}
        bibtex.Bibtex.member_items = lambda self, x: ("doi", str(x))
        self.memberitems_resp = [
            ["doi", "1"],
            ["doi", "2"],
            ["doi", "3"],
            ["doi", "4"],
        ]

        self.mi = models.MemberItems(bibtex.Bibtex(), self.r)

    def test_init(self):
        assert_equals(self.mi.__class__.__name__, "MemberItems")
        assert_equals(self.mi.provider.__class__.__name__, "Bibtex")

    def test_start_update(self):
        ret = self.mi.start_update("1234")
        input_hash = hashlib.md5("1234").hexdigest()
        assert_equals(input_hash, ret)

        sleep(.1) # give the thread a chance to finish.
        status = self.r.get_memberitems_status(input_hash)

        assert_equals(status["memberitems"], self.memberitems_resp )
        assert_equals(status["complete"], 4 )

    def test_get_sync(self):
        github.Github.member_items = lambda self, x: \
                [("github", name) for name in ["project1", "project2", "project3"]]
        synch_mi = models.MemberItems(github.Github(), self.r)

        # we haven't put q in redis with MemberItems.start_update(q),
        # so this should update while we wait.
        ret = synch_mi.get_sync("jasonpriem")
        assert_equals(ret["pages"], 1)
        assert_equals(ret["complete"], 1)
        assert_equals(ret["memberitems"],
            [
                ("github", "project1"),
                ("github", "project2"),
                ("github", "project3")
            ]
        )


    def test_get_async(self):
        ret = self.mi.start_update("1234")
        sleep(.1)
        res = self.mi.get_async(ret)
        print res
        assert_equals(res["complete"], 4)
        assert_equals(res["memberitems"], self.memberitems_resp)



