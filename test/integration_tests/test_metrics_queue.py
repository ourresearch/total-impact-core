import os, unittest, time, json
from nose.tools import nottest, assert_equals
from urllib import quote_plus
from nose.plugins.skip import SkipTest

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
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
        self.d = dao.Dao(self.testing_db_name, self.app.config["DB_URL"],
            self.app.config["DB_USERNAME"], self.app.config["DB_PASSWORD"])

        self.providers = ProviderFactory.get_providers(self.app.config["PROVIDERS"])


    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name

    def test_metrics_queue(self):
        """ Test that the metrics queue works

            This test isn't correct just now. We'd need to simulate
            the item getting it's aliases completed.
        """
        raise SkipTest
        self.d.create_new_db_and_connect(self.testing_db_name)
        number_of_item_api_calls = 0

        # create new dryad item 
        dryad_resp = self.client.post('/item/doi/' + 
                quote_plus(DRYAD_TEST_DOI))
        number_of_item_api_calls += 1
        dryad_tiid = dryad_resp.data

        # test the metrics view works
        res = self.d.view("metrics")
        assert_equals(
            len(res["rows"]),
             number_of_item_api_calls*len(self.providers)
            )  # three IDs above, three providers
        assert_equals(
            res["rows"][0]["value"]["metrics"]["dryad:package_views"]["values"],
            {})

        # see if the item is on the queue
        all_metrics_queue = MetricsQueue(self.d) 
        assert isinstance(all_metrics_queue.queue, list)
        assert_equals(
            len(all_metrics_queue.queue),
            number_of_item_api_calls*len(self.providers)
            )
        
        # get our item from the queue
        my_item = all_metrics_queue.dequeue() 
        assert_equals(my_item.metrics["dryad:package_views"]['values'], {})
        assert(my_item.created - time.time() < 30)


        # create new plos item 
        plos_resp = self.client.post('/item/doi/' + quote_plus(PLOS_TEST_DOI))
        number_of_item_api_calls += 1        
        plos_tiid = json.loads(plos_resp.data)

        # create new github item 
        github_resp = self.client.post('/item/github/' + quote_plus(GITHUB_TEST_ID))
        number_of_item_api_calls += 1        
        github_tiid = json.loads(github_resp.data)

        all_metrics_queue = MetricsQueue(self.d)
        #assert_equals(len(all_metrics_queue.queue), 
        #        number_of_item_api_calls*len(self.providers)) 

        dryad_metrics_queue = MetricsQueue(self.d, "dryad")
        assert_equals(len(dryad_metrics_queue.queue), 
                number_of_item_api_calls) 

        github_metrics_queue = MetricsQueue(self.d, "github")
        assert_equals(len(github_metrics_queue.queue), 
                number_of_item_api_calls) 


        alias_thread = ProvidersAliasThread(self.providers, self.d)
        alias_thread.run(run_only_once=True)

        # now run just the dryad metrics thread.
        metrics_thread = ProviderMetricsThread(self.providers[0], self.d)
        metrics_thread.run(run_only_once=True)  
        metrics_thread.run(run_only_once=True)
        metrics_thread.run(run_only_once=True)

        # test the dryad doi
        dryad_resp = self.client.get('/item/' + dryad_tiid.replace('"', ''))

        resp_dict = json.loads(dryad_resp.data)
        print json.dumps(resp_dict, sort_keys=True, indent=4) 

        assert_equals(resp_dict['metrics']['dryad:total_downloads']['values'].values()[0],
            169)


        #assert 100 < resp_dict["metrics"]["bucket"]["dryad"]["file_views"]["latest"]["value"] < 1000, resp_dict


"""
        # test the plos doi
        plos_resp = self.client.get('/item/' + plos_tiid)
        resp_dict = json.loads(plos_resp.data)
        assert_equals(
            resp_dict["aliases"]["title"][0],
            "Clickstream Data Yields High-Resolution Maps of Science"
            )
        # It's not in the spec, but I think we want a "latest" metric, so that
        # client code doesn't have to sort.
        assert 90 < resp_dict["metrics"]["mendeley"]["readers"]["latest"]["value"] < 100, resp_dict

        # test the GitHub ID
        github_resp = self.client.get('/item/' + github_tiid)
        resp_dict = json.loads(github_resp.data)
        assert_equals(
            resp_dict["aliases"]["url"][0],
            "https://github.com/mxcl/homebrew"
            )

        assert 5000 < resp_dict["metrics"]["github"]["watchers"]["latest"]["value"] < 10000, resp_dict
"""
