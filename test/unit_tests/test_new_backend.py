import json, os, Queue

from totalimpact import dao, tiredis, new_backend
from totalimpact.providers.provider import Provider, ProviderTimeout, ProviderFactory
from nose.tools import raises, assert_equals, nottest
from test.utils import http


class TestBackend():
    
    def setUp(self):
        self.config = None #placeholder
        TEST_PROVIDER_CONFIG = [
            ("wikipedia", {})
        ]
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))

        # do the same thing for the redis db
        self.r = tiredis.from_url("redis://localhost:6379")
        self.r.flushdb()

        self.b = new_backend.Backend([Queue.Queue()], self.r, self.d)

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


class TestBackendClass(TestBackend):

    def test_push_on_update_queue(self):
        self.b.push_on_update_queue(self.tiid, self.fake_aliases)
        expected = [u'abcd', {u'pmid': [u'111']}]
        in_queue = json.loads(self.r.rpop("alias"))
        assert_equals(in_queue, expected)

    def test_pop_from_update_queue_when_empty(self):
        response = self.b.pop_from_update_queue()
        assert_equals(response, None)

    def test_pop_from_update_queue_after_push(self):
        self.b.push_on_update_queue(self.tiid, self.fake_aliases)
        response = self.b.pop_from_update_queue()
        expected = [u'abcd', {u'pmid': [u'111']}]
        assert_equals(response, expected)

    def test_decide_who_to_call_next_unknown(self):
        unknown_item = {"aliases":{"unknownnamespace":["111"]},"biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(unknown_item)
        print response
        # expect blanks
        expected = {'metrics': [], 'biblio': [], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_webpage_no_title(self):
        webpage_item = {"aliases":{"url":["http://a"]},"biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(webpage_item)
        print response
        # expect all metrics and lookup the biblio
        expected = {'metrics': "all", 'biblio': ["webpage"], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_webpage_with_title(self):
        webpage_item = {"aliases":{"url":["http://a"]},"biblio":{"title":"hi"},"metrics":{}}
        response = self.b.decide_who_to_call_next(webpage_item)
        print response
        # expect all metrics, no need to look up biblio
        expected = {'metrics': "all", 'biblio': [], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_slideshare_no_title(self):
        slideshare_item = {"aliases":{"url":["http://abc.slideshare.net/def"]},"biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(slideshare_item)
        print response
        # expect all metrics and look up the biblio
        expected = {'metrics': "all", 'biblio': ["slideshare"], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_dryad_no_url(self):
        dryad_item = {"aliases":{"doi":["10.5061/dryad.3td2f"]},"biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(dryad_item)
        print response
        # expect need to resolve the dryad doi before can go get metrics
        expected = {'metrics': [], 'biblio': [], 'aliases': ['dryad']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_dryad_with_url(self):
        dryad_item = {"aliases":{   "doi":["10.5061/dryad.3td2f"],
                                    "url":["http://dryadsomewhere"]},
                    "biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(dryad_item)
        print response
        # have url so now can go get all the metrics
        expected = {'metrics': 'all', 'biblio': ['dryad'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_pmid_no_urls(self):
        pubmed_item = {"aliases":{"pmid":["111"]},"biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(pubmed_item)
        print response
        # expect need to get more aliases
        expected = {'metrics': [], 'biblio': [], 'aliases': ['pubmed', 'crossref']}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_pmid_with_urls(self):
        pubmed_item = {"aliases":{   "pmid":["1111"],
                                    "url":["http://pubmedsomewhere"]},
                    "biblio":{},"metrics":{}}
        response = self.b.decide_who_to_call_next(pubmed_item)
        print response
        # expect need to get metrics and biblio
        expected = {'metrics': 'all', 'biblio': ['pubmed'], 'aliases': []}
        assert_equals(response, expected)

    def test_decide_who_to_call_next_doi_with_urls(self):
        doi_item = {"aliases":{   "doi":["10.234/345345"],
                                    "url":["http://journalsomewhere"]},
                        "biblio":{},
                        "metrics":{}}
        response = self.b.decide_who_to_call_next(doi_item)
        print response
        # expect need to get metrics, biblio from crossref
        expected = {'metrics': 'all', 'biblio': ["crossref"], 'aliases': []}
        assert_equals(response, expected)     

    def test_decide_who_to_call_next_doi_with_urls_and_title(self):
        doi_item = {"aliases":{   "doi":["10.234/345345"],
                                    "url":["http://journalsomewhere"]},
                        "biblio":{"title":"something"},
                        "metrics":{}}
        response = self.b.decide_who_to_call_next(doi_item)
        print response
        # expect need to get metrics, no biblio
        expected = {'metrics': 'all', 'biblio': [], 'aliases': []}
        assert_equals(response, expected)   

    # warning: calls live provider right now
    @http
    def test_wrapper_aliases_to_update_queue(self):      
        response = self.b.wrapper(("mytiid", 
                {"doi":["10.5061/dryad.3td2f"]}, 
                ["dryad"], 
                "aliases", 
                self.b.add_aliases_to_update_queue))

        # test that it returned the correct item        
        expected = [[('url', u'http://hdl.handle.net/10255/dryad.33863'), ('title', u'data from: public sharing of research datasets: a pilot study of associations')]]
        assert_equals(response, expected)

        # test that it put it on the queue as per the callback
        in_queue = json.loads(self.r.rpop("alias"))
        expected = [('url', u'http://hdl.handle.net/10255/dryad.33863'), ('title', u'data from: public sharing of research datasets: a pilot study of associations')]
        assert_equals(in_queue, expected)

    # warning: calls live provider right now
    @http
    def test_wrapper_aliases_to_couch_queue(self):     
        response = self.b.wrapper(("mytiid", 
                {"doi":["10.5061/dryad.3td2f"]}, ["dryad"], "biblio", self.b.push_on_couch_queue))

        # test that it returned the correct item        
        expected = [{'authors': u'Piwowar, Chapman, Piwowar, Chapman, Piwowar, Chapman', 'year': u'2011', 'repository': 'Dryad Digital Repository', 'title': u'Data from: Public sharing of research datasets: a pilot study of associations'}]
        assert_equals(response, expected)

        # test that it put it on the queue as per the callback
        in_queue = self.b.pop_from_couch_queue()
        expected = ('mytiid', 'biblio', {'authors': u'Piwowar, Chapman, Piwowar, Chapman, Piwowar, Chapman', 'year': u'2011', 'repository': 'Dryad Digital Repository', 'title': u'Data from: Public sharing of research datasets: a pilot study of associations'})
        assert_equals(in_queue, expected)

