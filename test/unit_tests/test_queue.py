import unittest, json

from totalimpact import queue
from totalimpact import models

from nose.tools import nottest

class TestQueue(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.TESTDB = 'ti_test'
        ## FIXME refactor the line below to use the same method for the item seed as test_models
        ##cls.item = models.Item(**json.load(open('./test/totalimpact/item.json')))
        cls.item.config.db_name = cls.TESTDB
        cls.couch, cls.db = cls.item.connection()
        cls.item.save()

    @classmethod
    def teardown_class(cls):
        cls.couch.delete( cls.TESTDB )

    @nottest
    def test_alias_queue(self):
        aq = queue.AliasQueue()
        aq.config.db_name = self.TESTDB
        self.assertTrue( isinstance(aq.queue,list) ) 
        assert len(aq.queue) == 1, aq
        first = aq.first()
        assert first.id == self.item.id, first
        aq.save_and_unqueue(first)
        # TODO: once queues actually work, this should succeed
        assert len(aq.queue) == 0, aq

    @nottest
    def test_02_metrics_queue(self):
        mq = queue.MetricsQueue()
        mq.config.db_name = self.TESTDB
        mq.provider = 'Wikipedia'
        assert mq.provider == 'Wikipedia', mq
        self.assertTrue( isinstance(mq.queue,list) ) 
        assert len(mq.queue) == 1, mq
        first = mq.first()
        assert first.id == self.item.id, first
        mq.save_and_unqueue(first)
        # TODO: once queues actually work, this should succeed
        assert len(mq.queue) == 0, mq
        

