import os, unittest, time
from nose.tools import nottest, assert_equals

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.config import Configuration
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
from totalimpact.util import slow
from totalimpact import dao
from totalimpact.tilogging import logging

logger = logging.getLogger(__name__)

class TestAliasQueue(unittest.TestCase):
        
    def test_alias_queue(self):
        config = Configuration()
        providers = ProviderFactory.get_providers(config)

        mydao = dao.Dao(config)
        db_name = 'alias_queue_test'
        # Make sure we start with a fresh DB for testing: delete and create
        if mydao.db_exists(db_name):
            mydao.delete_db(db_name)
        mydao.create_db(db_name)
        mydao.connect()

        watcher = TotalImpactBackend(config)
        my_alias_queue = AliasQueue(mydao)
        assert isinstance(my_alias_queue.queue, list)
        assert len(my_alias_queue.queue) > 1

        first = my_alias_queue.first()
        print first["_id"]

        ### FIXME Need to make first return an Item so that can pass to save_and_unqueue

        assert len(first["_id"]) > 1
        ## FIXME my_alias_queue.save_and_unqueue(first)

        # TODO: once queues actually work, this should succeed
        ## FIXME assert_equals(len(my_alias_queue.queue), 0)


