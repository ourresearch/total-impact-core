import json, os, Queue, datetime

from totalimpact import tiredis, backend, default_settings
from totalimpact import db, app
from totalimpact import item as item_module
from totalimpact.providers.provider import Provider, ProviderTimeout, ProviderFactory
from totalimpact import REDIS_UNITTEST_DATABASE_NUMBER

from nose.tools import raises, assert_equals, nottest
from test.utils import slow
from test import mocks

from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests


class TestBackend():
    
    def setUp(self):
        self.config = None #placeholder
        self.TEST_PROVIDER_CONFIG = [
            ("wikipedia", {})
        ]
        self.d = None

        # do the same thing for the redis db, set up the test redis database.  We're using DB Number 8
        self.r = tiredis.from_url("redis://localhost:6379", db=REDIS_UNITTEST_DATABASE_NUMBER)
        self.r.flushdb()

        provider_queues = {}
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG)
        for provider in providers:
            provider_queues[provider.provider_name] = backend.PythonQueue(provider.provider_name+"_queue")

        self.b = backend.Backend(
            backend.RedisQueue("alias-unittest", self.r), 
            provider_queues, 
            [backend.PythonQueue("couch_queue")], 
            self.r)

        self.fake_item = {
            "_id": "1",
            "type": "item",
            "num_providers_still_updating":1,
            "aliases":{"pmid":["111"]},
            "biblio": {},
            "metrics": {},
            "last_modified": datetime.datetime(2013, 1, 1)
        }
        self.fake_aliases_dict = {"pmid":["222"]}
        self.tiid = "abcd"

        self.db = setup_postgres_for_unittests(db, app)


    def teardown(self):
        self.r.flushdb()

        teardown_postgres_for_unittests(self.db)



class TestProviderWorker(TestBackend):
    # warning: calls live provider right now
    def test_add_to_couch_queue_if_nonzero(self):    
        test_couch_queue = backend.PythonQueue("test_couch_queue")
        provider_worker = backend.ProviderWorker(mocks.ProviderMock("myfakeprovider"), 
                                        None, None, None, {"a": test_couch_queue}, None, self.r)  
        response = provider_worker.add_to_couch_queue_if_nonzero("aaatiid", #start fake tiid with "a" so in first couch queue
                {"doi":["10.5061/dryad.3td2f"]}, 
                "aliases", 
                "dummy")

        # test that it put it on the queue
        in_queue = test_couch_queue.pop()
        expected = {'method_name': 'aliases', 'tiid': 'aaatiid', 'provider_name': 'myfakeprovider', 'analytics_credentials': 'dummy', 'new_content': {'doi': ['10.5061/dryad.3td2f']}}
        assert_equals(in_queue, expected)

    def test_add_to_couch_queue_if_nonzero_given_metrics(self):    
        test_couch_queue = backend.PythonQueue("test_couch_queue")
        provider_worker = backend.ProviderWorker(mocks.ProviderMock("myfakeprovider"), 
                                        None, None, None, {"a": test_couch_queue}, None, self.r)  
        metrics_method_response = {'dryad:package_views': (361, 'http://dx.doi.org/10.5061/dryad.7898'), 
                    'dryad:total_downloads': (176, 'http://dx.doi.org/10.5061/dryad.7898'), 
                    'dryad:most_downloaded_file': (65, 'http://dx.doi.org/10.5061/dryad.7898')}        
        response = provider_worker.add_to_couch_queue_if_nonzero("aaatiid", #start fake tiid with "a" so in first couch queue
                metrics_method_response,
                "metrics", 
                "dummy")

        # test that it put it on the queue
        in_queue = test_couch_queue.pop()
        expected = {'method_name': 'metrics', 'tiid': 'aaatiid', 'provider_name': 'myfakeprovider', 'analytics_credentials': 'dummy', 'new_content': metrics_method_response}
        print in_queue
        assert_equals(in_queue, expected)        

        # check nothing in redis since it had a value
        response = self.r.get_num_providers_currently_updating("aaatiid")
        assert_equals(response, 0)

    def test_add_to_couch_queue_if_nonzero_given_empty_metrics_response(self):    
        test_couch_queue = backend.PythonQueue("test_couch_queue")
        provider_worker = backend.ProviderWorker(mocks.ProviderMock("myfakeprovider"), 
                                        None, None, None, {"a": test_couch_queue}, None, self.r)  
        metrics_method_response = {}
        response = provider_worker.add_to_couch_queue_if_nonzero("aaatiid", #start fake tiid with "a" so in first couch queue
                metrics_method_response,
                "metrics", 
                "dummy")

        # test that it did not put it on the queue
        in_queue = test_couch_queue.pop()
        expected = None
        assert_equals(in_queue, expected)        

        # check decremented in redis since the payload was null
        response = num_left = self.r.get_num_providers_currently_updating("aaatiid")
        assert_equals(response, 0)

    def test_wrapper(self):     
        def fake_callback(tiid, new_content, method_name, analytics_credentials, aliases_providers_run):
            pass

        response = backend.ProviderWorker.wrapper("123", 
                {'url': ['http://somewhere'], 'doi': ['10.123']}, 
                mocks.ProviderMock("myfakeprovider"), 
                "aliases", 
                {}, # credentials
                [], # aliases previously run
                fake_callback)
        print response
        expected = {'url': ['http://somewhere'], 'doi': ['10.1', '10.123']}
        assert_equals(response, expected)

class TestCouchWorker(TestBackend):
    def test_update_item_with_new_aliases(self):
        response = backend.CouchWorker.update_item_with_new_aliases(self.fake_aliases_dict, self.fake_item)
        expected = {'metrics': {}, 'num_providers_still_updating': 1, 'biblio': {}, '_id': '1', 'type': 'item', 
            'aliases': {'pmid': ['222', '111']}, 'last_modified': datetime.datetime(2013, 1, 1, 0, 0)}
        assert_equals(response, expected)

    def test_update_item_with_new_aliases_using_dup_alias(self):
        dup_alias_dict = self.fake_item["aliases"]
        response = backend.CouchWorker.update_item_with_new_aliases(dup_alias_dict, self.fake_item)
        expected = None # don't return the item if it already has all the aliases in it
        assert_equals(response, expected)

    def test_update_item_with_new_biblio(self):
        new_biblio_dict = {"title":"A very good paper", "authors":"Smith, Lee, Khun"}
        response = backend.CouchWorker.update_item_with_new_biblio(new_biblio_dict, self.fake_item)
        expected = new_biblio_dict
        assert_equals(response["biblio"], expected)

    def test_update_item_with_new_biblio_existing_biblio(self):
        item_with_some_biblio = self.fake_item
        item_with_some_biblio["biblio"] = {"title":"Different title"}
        new_biblio_dict = {"title":"A very good paper", "authors":"Smith, Lee, Khun"}
        response = backend.CouchWorker.update_item_with_new_biblio(new_biblio_dict, item_with_some_biblio)
        expected = {"authors": new_biblio_dict["authors"]}
        assert_equals(response["biblio"], expected)

    def test_update_item_with_new_metrics(self):
        response = backend.CouchWorker.update_item_with_new_metrics("mendeley:groups", (3, "http://provenance"), self.fake_item)
        expected = {'mendeley:groups': {'provenance_url': 'http://provenance', 'values': {'raw': 3, 'raw_history': {'2012-09-15T21:39:39.563710': 3}}}}
        print response["metrics"]        
        assert_equals(response["metrics"]['mendeley:groups']["provenance_url"], 'http://provenance')
        assert_equals(response["metrics"]['mendeley:groups']["values"]["raw"], 3)
        assert_equals(response["metrics"]['mendeley:groups']["values"]["raw_history"].values(), [3])
        # check year starts with 20
        assert_equals(response["metrics"]['mendeley:groups']["values"]["raw_history"].keys()[0][0:2], "20")

    def test_run_nothing_in_queue(self):
        test_couch_queue = backend.PythonQueue("test_couch_queue")
        couch_worker = backend.CouchWorker(test_couch_queue, self.r, self.d)
        response = couch_worker.run()
        expected = None
        assert_equals(response, expected)

    def test_run_aliases_in_queue(self):
        test_couch_queue = backend.PythonQueue("test_couch_queue")
        test_couch_queue_dict = {self.fake_item["_id"][0]:test_couch_queue}
        provider_worker = backend.ProviderWorker(mocks.ProviderMock("myfakeprovider"), 
                                        None, None, None, test_couch_queue_dict, None, self.r)  
        response = provider_worker.add_to_couch_queue_if_nonzero(self.fake_item["_id"], 
                {"doi":["10.5061/dryad.3td2f"]}, 
                "aliases", 
                "dummy")

        # save basic item beforehand
        item_obj = item_module.create_objects_from_item_doc(self.fake_item)
        self.db.session.add(item_obj)
        self.db.session.commit()

        # run
        couch_worker = backend.CouchWorker(test_couch_queue, self.r, self.d)
        response = couch_worker.run()
        expected = None
        assert_equals(response, expected)

        # check couch_queue has value after
        response = item_module.get_item(self.fake_item["_id"], {}, self.r)
        print response
        expected = {'pmid': ['111'], 'doi': ['10.5061/dryad.3td2f']}
        assert_equals(response["aliases"], expected)

        # check has updated last_modified time
        now = datetime.datetime.utcnow().isoformat()
        assert_equals(response["last_modified"][0:10], now[0:10])

    def test_run_metrics_in_queue(self):
        test_couch_queue = backend.PythonQueue("test_couch_queue")
        test_couch_queue_dict = {self.fake_item["_id"][0]:test_couch_queue}
        provider_worker = backend.ProviderWorker(mocks.ProviderMock("myfakeprovider"), 
                                        None, None, None, test_couch_queue_dict, None, self.r) 
        metrics_method_response = {'dryad:package_views': (361, 'http://dx.doi.org/10.5061/dryad.7898'), 
                            'dryad:total_downloads': (176, 'http://dx.doi.org/10.5061/dryad.7898'), 
                            'dryad:most_downloaded_file': (65, 'http://dx.doi.org/10.5061/dryad.7898')}                                         
        response = provider_worker.add_to_couch_queue_if_nonzero(self.fake_item["_id"], 
                metrics_method_response,
                "metrics", 
                "dummy")

        # save basic item beforehand
        item_obj = item_module.create_objects_from_item_doc(self.fake_item)
        self.db.session.add(item_obj)
        self.db.session.commit()

        # run
        couch_worker = backend.CouchWorker(test_couch_queue, self.r, self.d)    
        couch_worker.run()
            
        # check couch_queue has value after
        response = item_module.get_item(self.fake_item["_id"], {}, self.r)
        print response
        expected = 361
        assert_equals(response["metrics"]['dryad:package_views']['values']["raw"], expected)


class TestBackendClass(TestBackend):

    def test_decide_who_to_call_next_unknown(self):
        aliases_dict = {"unknownnamespace":["111"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect blanks
        expected = {'metrics': [], 'biblio': [], 'aliases': ['webpage']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_unknown_after_webpage(self):
        aliases_dict = {"unknownnamespace":["111"]}
        prev_aliases = ["webpage"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect blanks
        expected = {'metrics': ["wikipedia"], 'biblio': ["webpage"], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_webpage_no_title(self):
        aliases_dict = {"url":["http://a"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect all metrics and lookup the biblio
        expected = {'metrics': ['wikipedia'], 'biblio': ['webpage'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_webpage_with_title(self):
        aliases_dict = {"url":["http://a"], "title":["A Great Paper"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect all metrics, no need to look up biblio
        expected = {'metrics': ['wikipedia'], 'biblio': ['webpage'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_slideshare_no_title(self):
        aliases_dict = {"url":["http://abc.slideshare.net/def"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect all metrics and look up the biblio
        expected = {'metrics': ['wikipedia'], 'biblio': ['slideshare'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_dryad_no_url(self):
        aliases_dict = {"doi":["10.5061/dryad.3td2f"]}
        prev_aliases = ["altmetric_com"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to resolve the dryad doi before can go get metrics
        expected = {'metrics': [], 'biblio': [], 'aliases': ['dryad']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_dryad_with_url(self):
        aliases_dict = {   "doi":["10.5061/dryad.3td2f"],
                                    "url":["http://dryadsomewhere"]}
        prev_aliases = ["altmetric_com"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # still need the dx.doi.org url
        expected = {'metrics': [], 'biblio': [], 'aliases': ['dryad']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_dryad_with_doi_url(self):
        aliases_dict = {   "doi":["10.5061/dryad.3td2f"],
                                    "url":["http://dx.doi.org/10.dryadsomewhere"]}
        prev_aliases = ["altmetric_com", "dryad"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # have url so now can go get all the metrics
        expected = {'metrics': ['wikipedia'], 'biblio': ['dryad', 'mendeley'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_crossref_not_run(self):
        aliases_dict = {"pmid":["111"]}
        prev_aliases = ["mendeley"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get more aliases
        expected = {'metrics': [], 'biblio': [], 'aliases': ['crossref']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_pmid_mendeley_not_run(self):
        aliases_dict = {"pmid":["111"]}
        prev_aliases = [""]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get more aliases
        expected = {'metrics': [], 'biblio': [], 'aliases': ['mendeley']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_pmid_prev_run(self):
        aliases_dict = {  "pmid":["1111"],
                         "url":["http://pubmedsomewhere"]}
        prev_aliases = ["pubmed", "mendeley"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics and biblio
        expected = {'metrics': [], 'biblio': [], 'aliases': ['crossref']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_doi_with_urls(self):
        aliases_dict = {  "doi":["10.234/345345"],
                                "url":["http://journalsomewhere"]}
        prev_aliases = ["pubmed", "mendeley"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics, biblio from crossref
        expected = {'metrics': [], 'biblio': [], 'aliases': ['crossref']}
        assert_equals(response, expected)     

    def test_decide_who_to_call_next_doi_crossref_prev_called(self):
        aliases_dict = { "doi":["10.234/345345"],
                        "url":["http://journalsomewhere"]}
        prev_aliases = ["crossref"]                        
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics, no biblio
        expected = {'metrics': [], 'biblio': [], 'aliases': ['mendeley']}
        assert_equals(response, expected)   

    def test_decide_who_to_call_next_doi_crossref_pubmed_mendeley_prev_called(self):
        aliases_dict = { "doi":["10.234/345345"],
                        "url":["http://journalsomewhere"]}
        prev_aliases = ["crossref", "pubmed", "mendeley", "altmetric_com"]                        
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics, no biblio
        expected = {'metrics': ['wikipedia'], 'biblio': ['crossref', 'pubmed', 'mendeley', 'webpage'], 'aliases': []}
        assert_equals(response, expected)   

    def test_decide_who_to_call_next_pmid_crossref_pubmed_prev_called(self):
        aliases_dict = { "pmid":["1111"],
                        "url":["http://journalsomewhere"]}
        prev_aliases = ["crossref", "pubmed", "mendeley", "altmetric_com"]                        
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics, no biblio
        expected = {'metrics': ['wikipedia'], 'biblio': ['crossref', 'pubmed', 'mendeley', 'webpage'], 'aliases': []}
        assert_equals(response, expected)   


