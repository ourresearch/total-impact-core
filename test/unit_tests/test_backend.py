import json, os, Queue

from totalimpact import dao, tiredis, backend, default_settings
from totalimpact.providers.provider import Provider, ProviderTimeout, ProviderFactory
from nose.tools import raises, assert_equals, nottest
from test.utils import slow
from test import mocks


class TestBackend():
    
    def setUp(self):
        self.config = None #placeholder
        self.TEST_PROVIDER_CONFIG = [
            ("wikipedia", {})
        ]
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))

        # do the same thing for the redis db
        self.r = tiredis.from_url("redis://localhost:6379")
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
            "metrics": {}
        }
        self.fake_aliases = {"pmid":["111"]}
        self.tiid = "abcd"

    def teardown(self):
        self.d.delete_db(os.environ["CLOUDANT_DB"])
        self.r.flushdb()


class TestProviderWorker(TestBackend):
    # warning: calls live provider right now
    @nottest
    def test_wrapper_aliases_to_update_queue(self):      
        response = backend.ProviderWorker.wrapper("mytiid", 
                {"doi":["10.5061/dryad.3td2f"]}, 
                ["dryad"], 
                "aliases", 
                self.b.add_aliases_to_update_queue)

        # test that it put it on the queue as per the callback
        in_queue = self.r.rpop("alias")
        expected = [('url', u'http://hdl.handle.net/10255/dryad.33863'), ('title', u'data from: public sharing of research datasets: a pilot study of associations')]
        assert_equals(in_queue, expected)

        # test that it returned the correct item        
        expected = [[('url', u'http://hdl.handle.net/10255/dryad.33863'), ('title', u'data from: public sharing of research datasets: a pilot study of associations')]]
        assert_equals(response, expected)

    # warning: calls live provider right now
    @nottest
    def test_wrapper_aliases_to_couch_queue(self):     
        response = backend.ProviderWorker.wrapper("mytiid", 
                {"doi":["10.5061/dryad.3td2f"]}, ["dryad"], "biblio", self.b.push_on_couch_queue)

        # test that it returned the correct item        
        expected = [{'authors': u'Piwowar, Chapman, Piwowar, Chapman, Piwowar, Chapman', 'year': u'2011', 'repository': 'Dryad Digital Repository', 'title': u'Data from: Public sharing of research datasets: a pilot study of associations'}]
        assert_equals(response, expected)

        # test that it put it on the queue as per the callback
        in_queue = self.b.pop_from_couch_queue()
        expected = ('mytiid', 'biblio', {'authors': u'Piwowar, Chapman, Piwowar, Chapman, Piwowar, Chapman', 'year': u'2011', 'repository': 'Dryad Digital Repository', 'title': u'Data from: Public sharing of research datasets: a pilot study of associations'})
        assert_equals(in_queue, expected)

    def test_wrapper(self):     
        def fake_callback(tiid, new_content, method_name, aliases_providers_run):
            pass

        response = backend.ProviderWorker.wrapper("123", 
                {'url': ['http://somewhere'], 'doi': ['10.123']}, 
                mocks.ProviderMock("myfakeprovider"), 
                "aliases", 
                [], # aliases previously run
                fake_callback)
        expected = {'url': ['http://somewhere'], 'doi': ['10.123']}
        assert_equals(response, expected)


class TestBackendClass(TestBackend):

    def test_decide_who_to_call_next_unknown(self):
        aliases_dict = {"unknownnamespace":["111"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect blanks
        expected = {'metrics': ["wikipedia"], 'biblio': [], 'aliases': []}
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
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to resolve the dryad doi before can go get metrics
        expected = {'metrics': [], 'biblio': [], 'aliases': ['dryad']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_dryad_with_url(self):
        aliases_dict = {   "doi":["10.5061/dryad.3td2f"],
                                    "url":["http://dryadsomewhere"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # have url so now can go get all the metrics
        expected = {'metrics': ['wikipedia'], 'biblio': ['dryad'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_pmid_not_run(self):
        aliases_dict = {"pmid":["111"]}
        prev_aliases = []
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get more aliases
        expected = {'metrics': [], 'biblio': [], 'aliases': ['pubmed']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_pmid_prev_run(self):
        aliases_dict = {  "pmid":["1111"],
                         "url":["http://pubmedsomewhere"]}
        prev_aliases = ["pubmed"]
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics and biblio
        expected = {'metrics': [], 'biblio': [], 'aliases': ['crossref']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_doi_with_urls(self):
        aliases_dict = {  "doi":["10.234/345345"],
                                "url":["http://journalsomewhere"]}
        prev_aliases = ["pubmed"]
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
        expected = {'metrics': [], 'biblio': [], 'aliases': ['pubmed']}
        assert_equals(response, expected)   

    def test_decide_who_to_call_next_doi_crossref_pubmed_prev_called(self):
        aliases_dict = { "doi":["10.234/345345"],
                        "url":["http://journalsomewhere"]}
        prev_aliases = ["crossref", "pubmed"]                        
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics, no biblio
        expected = {'metrics': ["wikipedia"], 'biblio': ['pubmed', 'crossref'], 'aliases': []}
        assert_equals(response, expected)   

    def test_decide_who_to_call_next_pmid_crossref_pubmed_prev_called(self):
        aliases_dict = { "pmid":["1111"],
                        "url":["http://journalsomewhere"]}
        prev_aliases = ["crossref", "pubmed"]                        
        response = backend.Backend.sniffer(aliases_dict, prev_aliases, self.TEST_PROVIDER_CONFIG)
        print response
        # expect need to get metrics, no biblio
        expected = {'metrics': ["wikipedia"], 'biblio': ['pubmed', 'crossref'], 'aliases': []}
        assert_equals(response, expected)   


