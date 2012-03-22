import os
import json
from nose.tools import assert_equal

import totalimpact.queue as queue
import totalimpact.config as config

class TestQueue:
    @classmethod
    def setup_class(cls):
        config["db_name"] = 'ti-test'
        pass

    @classmethod
    def teardown_class(cls):
        couch, db = dao.Dao.connection()
        del couch[ config["db_name"] ]

    def test_queue(self):
        pass

    def test_alias_queue(self):
        pass
        
    def test_metrics_queue(self):
        pass
        

