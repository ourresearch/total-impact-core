import os, unittest, time, json
from nose.tools import nottest, assert_equals

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.config import Configuration
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
from totalimpact.util import slow
from totalimpact import dao, api
from totalimpact.tilogging import logging

PLOS_TEST_DOI = "10.1371/journal.pone.0004803"
DRYAD_TEST_DOI = "10.5061/dryad.7898"
GITHUB_TEST_ID = "homebrew"

class TestMetricsQueue(unittest.TestCase):

    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True 
        self.client = self.app.test_client()

        # setup the database
        self.testing_db_name = "metrics_queue_test"
        self.old_db_name = self.app.config["DB_NAME"]
        self.app.config["DB_NAME"] = self.testing_db_name
        self.config = Configuration()
        self.d = dao.Dao(self.config)


    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name

    @nottest
    def test_metrics_queue(self):
        self.d.create_new_db_and_connect(self.testing_db_name)

        # create three new items from  plos and dryad dois
        plos_resp = self.client.post('/item/DOI/' + PLOS_TEST_DOI.replace("/", "%2F"))
        plos_tiid = plos_resp.data

        dryad_resp = self.client.post('/item/DOI/' + DRYAD_TEST_DOI.replace("/", "%2F"))
        dryad_tiid = plos_resp.data

        github_resp = self.client.post('/item/GitHub/' + GITHUB_TEST_ID)
        github_tiid = github_resp.data

        # do the update using the backend
        backend = TotalImpactBackend(config)

        # we need a new param to exit after a few seconds so we can finish testing
        backend.run(die_in=7)

        # test the plos doi
        plos_resp = self.client.get('/item/' + plos_tiid)
        resp_dict = json.loads(plos_resp.data)
        assert_equals(
            resp_dict["aliases"]["TITLE"][0],
            "Clickstream Data Yields High-Resolution Maps of Science"
            )
        # It's not in the spec, but I think we want a "latest" metric, so that
        # client code doesn't have to sort.
        assert 90 < resp_dict["metrics"]["Mendeley"]["readers"]["latest"]["value"] < 100, resp_dict

        # test the dryad doi
        dryad_resp = self.client.get('/item/' + dryad_tiid)
        resp_dict = json.loads(dryad_resp.data)
        assert_equals(
            resp_dict["aliases"]["TITLE"][0],
            "data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides"
            )

        assert 100 < resp_dict["metrics"]["Dryad"]["file_views"]["latest"]["value"] < 1000, resp_dict

        # test the GitHub ID
        github_resp = self.client.get('/item/' + github_tiid)
        resp_dict = json.loads(github_resp.data)
        assert_equals(
            resp_dict["aliases"]["URL"][0],
            "https://github.com/mxcl/homebrew"
            )

        assert 5000 < resp_dict["metrics"]["GitHub"]["watchers"]["latest"]["value"] < 10000, resp_dict
