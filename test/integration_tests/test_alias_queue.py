import os, unittest, time, json, yaml, json
from urllib import quote_plus
from nose.tools import nottest, assert_equals

from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.queue import Queue, AliasQueue, MetricsQueue, QueueMonitor
from totalimpact import dao, api
from totalimpact.tilogging import logging
from totalimpact.queue import AliasQueue, MetricsQueue

TEST_DRYAD_DOI = "10.5061/dryad.7898"

datadir = os.path.join(os.path.split(__file__)[0], "../../extras/sample_provider_pages/dryad")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")



def get_aliases_html_success(self, url, headers=None, timeout=None):
    if ("dc.contributor" in url):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
    else:
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())


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
        self.d = dao.Dao(self.testing_db_name, self.app.config["DB_URL"],
            self.app.config["DB_USERNAME"], self.app.config["DB_PASSWORD"])
       
        
    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name
        # Clear the queues of any items we have left around
        AliasQueue.clear()
        MetricsQueue.clear()

    def test_alias_queue(self):
        self.d.create_new_db_and_connect(self.testing_db_name)

        providers = ProviderFactory.get_providers(self.app.config["PROVIDERS"])

        response = self.client.post('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = json.loads(response.data)


        # now get it back out
        response = self.client.get('/item/' + tiid)
        print tiid
        assert_equals(response.status_code, 200)
        
        resp_dict = json.loads(response.data)
        assert_equals(
            set(resp_dict.keys()),
            set([u'tiid', u'created', u'last_requested', u'metrics', 
                u'last_modified', u'biblio', u'id', u'aliases', u'last_queued'])
            )
        assert_equals(unicode(TEST_DRYAD_DOI), resp_dict["aliases"]["doi"][0])
        print resp_dict

        # test the view works
        res = self.d.view("requested")
        assert len(res["rows"]) == 1, res
        assert_equals(resp_dict['id'], res["rows"][0]['id'])

        # Run the QueueMonitor 
        qm = QueueMonitor(self.d)
        qm.run(runonce=True)

        # see if the item is on the queue
        my_alias_queue = AliasQueue(self.d)
        
        # get our item from the queue
        my_item = my_alias_queue.first()
        assert_equals(my_item.aliases.doi[0], TEST_DRYAD_DOI)

        # do the update using the backend
        alias_thread = ProvidersAliasThread(providers, self.d)
        alias_thread.run(run_only_once=True)

        # get the item back out again and bask in the awesome
        response = self.client.get('/item/' + tiid)
        resp_dict = json.loads(response.data)
        print tiid
        print response.data
        assert_equals(
            resp_dict["aliases"]["title"][0],
            "data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides"
            )
        print resp_dict
        assert_equals(resp_dict["biblio"]["data"]["year"], "2010")

