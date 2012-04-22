import os, unittest, time, json
from nose.tools import nottest, assert_equals
from urllib import quote_plus

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.config import Configuration
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue
from totalimpact import dao, api
from totalimpact.tilogging import logging

PLOS_TEST_DOI = "10.1371/journal.pone.0004803"
DRYAD_TEST_DOI = "10.5061/dryad.7898"
GITHUB_TEST_ID = "homebrew"

datadir = os.path.join(os.path.split(__file__)[0], "../data")

DRYAD_CONFIG_FILENAME = "totalimpact/providers/dryad.conf.json"
TEST_DRYAD_DOI = "10.5061/dryad.7898"
TEST_DRYAD_AUTHOR = "Piwowar, Heather A."
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, 
    "sample_extract_metrics_page.html")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, 
    "sample_extract_aliases_page.xml")

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content

def get_metrics_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
    return DummyResponse(200, f.read())
def get_aliases_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())

PROVIDERS = [
    {
        "class" : "totalimpact.providers.dryad.Dryad",
        "config" : "totalimpact/providers/dryad.conf.json"
    }
]

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
        self.d = dao.Dao(self.testing_db_name)
        provider_configs = PROVIDERS
        self.providers = ProviderFactory.get_providers(provider_configs)

        # monkey patch http_get
        self.old_http_get = Provider.http_get


    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name
        Provider.http_get = self.old_http_get


    def test_metrics_queue(self):
        self.d.create_new_db_and_connect(self.testing_db_name)
        number_of_item_api_calls = 0

        # create new dryad item 
        dryad_resp = self.client.post('/item/doi/' + 
                quote_plus(DRYAD_TEST_DOI))
        number_of_item_api_calls += 1
        dryad_tiid = dryad_resp.data

        print self.providers

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
        my_item = all_metrics_queue.first() 
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

        Provider.http_get = get_aliases_html_success

        alias_thread = ProvidersAliasThread(self.providers, self.d)
        alias_thread.run(run_only_once=True)

        one_provider = self.providers[0]
        metrics_thread = ProviderMetricsThread(one_provider, self.d)

        Provider.http_get = get_metrics_html_success

        metrics_thread.run(run_only_once=True)

        # do the update using the backend
        #backend = TotalImpactBackend(self.d, self.providers)

        # we need a new param to exit after a few seconds so we can finish testing

        # test the dryad doi
        dryad_resp = self.client.get('/item/' + dryad_tiid)
        Provider.http_get = self.old_http_get

        resp_dict = json.loads(dryad_resp.data)

        #assert_equals(
        #    resp_dict["aliases"]["title"][0],
        #    "data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides"
        #    )

        print json.dumps(resp_dict, sort_keys=True, indent=4)

        hashes = resp_dict["metrics"]["bucket"].keys()
        print hashes
        print resp_dict["metrics"]["bucket"][hashes[0]]["id"]
        print resp_dict["metrics"]["bucket"][hashes[0]]["value"]
        print resp_dict["metrics"]["bucket"][hashes[0]]["static_meta"]["description"]

        assert 50 < int(resp_dict["metrics"]["bucket"][hashes[0]]["value"]) < 1000, resp_dict["metrics"]["bucket"][hashes[0]]["value"]

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
