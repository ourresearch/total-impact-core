import os, unittest, time, json
from nose.tools import nottest, assert_equals

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
from totalimpact import dao, api
from totalimpact.tilogging import logging

TEST_DRYAD_DOI = "10.5061/dryad.7898"

class TestAliasQueue(unittest.TestCase):
    
    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True
        self.client = self.app.test_client()
        
        # setup the database
        self.testing_db_name = "alias_queue_test"
        self.old_db_name = self.app.config["DB_NAME"]
        self.app.config["DB_NAME"] = self.testing_db_name
        self.d = dao.Dao(self.app.config["DB_NAME"])
       
        
    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name

    # Broken test.  See issue #90
    @nottest
    def test_alias_queue(self):
        self.d.create_new_db_and_connect(self.testing_db_name)

        providers = ProviderFactory.get_providers(self.app.config["PROVIDERS"])

        response = self.client.post('/item/doi/' + TEST_DRYAD_DOI.replace("/", "%2F"))
        tiid = response.data


        # now get it back out
        tiid = tiid.replace('"', '')
        response = self.client.get('/item/' + tiid)
        assert_equals(response.status_code, 200)
        
        resp_dict = json.loads(response.data)
        assert_equals(
            set(resp_dict.keys()),
            set([u'created', u'last_requested', u'metrics', u'last_modified', u'biblio', u'id', u'aliases'])
            )
        assert_equals(unicode(TEST_DRYAD_DOI), resp_dict["aliases"]["doi"])

        # test the view works
        res = self.d.view("aliases")
        assert len(res["rows"]) == 1, res
        assert_equals(res["rows"][0]["value"]["aliases"]["doi"], TEST_DRYAD_DOI)

        # see if the item is on the queue
        my_alias_queue = AliasQueue(self.d)
        assert isinstance(my_alias_queue.queue, list)
        assert_equals(len(my_alias_queue.queue), 1)
        
        # get our item from the queue
        my_item = my_alias_queue.first()
        assert_equals(my_item.aliases.data["doi"], TEST_DRYAD_DOI)

        # do the update using the backend
        alias_thread = ProvidersAliasThread(providers, self.d)
        alias_thread.run_once = True
        alias_thread.run()

        # get the item back out again and bask in the awesome
        response = self.client.get('/item/' + tiid)
        resp_dict = json.loads(response.data)
        assert_equals(
            resp_dict["aliases"]["title"][0],
            "data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides"
            ) 
