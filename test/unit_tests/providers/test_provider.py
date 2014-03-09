from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact import app, db
from nose.tools import assert_equals, nottest
from xml.dom import minidom 
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

import simplejson, BeautifulSoup
import os
from sqlalchemy.sql import text    

sampledir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/")

class Test_Provider():

    TEST_PROVIDER_CONFIG = [
        ("pubmed", { "workers":1 }),
        ("wikipedia", {"workers": 3}),
        ("mendeley", {"workers": 3}),
    ]
    
    TEST_JSON = """{"repository":{"homepage":"","watchers":7,"has_downloads":true,"fork":false,"language":"Java","has_issues":true,"has_wiki":true,"forks":0,"size":4480,"private":false,"created_at":"2008/09/29 04:26:42 -0700","name":"gtd","owner":"egonw","description":"Git-based ToDo tool.","open_issues":2,"url":"https://github.com/egonw/gtd","pushed_at":"2012/02/28 10:21:26 -0800"}}"""

    TEST_XML = open(os.path.join(sampledir, "facebook", "metrics")).read()

    def setUp(self):
        self.db = setup_postgres_for_unittests(db, app)
        
    def tearDown(self):
        teardown_postgres_for_unittests(self.db)

    def test_get_provider(self):
        provider = ProviderFactory.get_provider("wikipedia")
        assert_equals(provider.__class__.__name__, "Wikipedia")
        
    def test_get_providers(self):
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG)
        provider_names = [provider.__class__.__name__ for provider in providers]
        assert_equals(set(provider_names), set(['Mendeley', 'Wikipedia', "Pubmed"]))

    def test_get_providers_filters_by_metrics(self):
        # since all the providers do metrics, "metrics" arg changes nought.
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG, "metrics")
        provider_names = [provider.__class__.__name__ for provider in providers]
        assert_equals(set(provider_names), set(['Mendeley', 'Wikipedia', "Pubmed"]))

    def test_get_providers_filters_by_biblio(self):
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG, "biblio")
        provider_names = [provider.__class__.__name__ for provider in providers]
        assert_equals(set(provider_names), set(['Pubmed', 'Mendeley']))

    def test_get_providers_filters_by_aliases(self):
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG, "aliases")
        provider_names = [provider.__class__.__name__ for provider in providers]
        assert_equals(set(provider_names), set(['Pubmed', 'Mendeley']))

    def test_lookup_json(self):
        page = self.TEST_JSON
        data = simplejson.loads(page)
        response = provider._lookup_json(data, ['repository', 'name'])
        assert_equals(response, u'gtd')

    def test_extract_json(self):
        page = self.TEST_JSON
        dict_of_keylists = {
            'title' : ['repository', 'name'],
            'description' : ['repository', 'description']}

        response = provider._extract_from_json(page, dict_of_keylists)
        assert_equals(response, {'description': u'Git-based ToDo tool.', 'title': u'gtd'})
    
    def test_lookup_xml_from_dom(self):
        page = self.TEST_XML
        doc = minidom.parseString(page.strip())
        response = provider._lookup_xml_from_dom(doc, ['total_count'])
        assert_equals(response, 17)

    def test_lookup_xml_from_soup(self):
        page = self.TEST_XML
        doc = BeautifulSoup.BeautifulStoneSoup(page) 
        response = provider._lookup_xml_from_soup(doc, ['total_count'])
        assert_equals(response, 17)

    def test_extract_xml(self):
        page = self.TEST_XML
        dict_of_keylists = {
            'count' : ['total_count']}

        response = provider._extract_from_xml(page, dict_of_keylists)
        assert_equals(response, {'count': 17})

    def test_doi_from_url_string(self):
        test_url = "https://knb.ecoinformatics.org/knb/d1/mn/v1/object/doi:10.5063%2FAA%2Fnrs.373.1"
        expected = "10.5063/AA/nrs.373.1"
        response = provider.doi_from_url_string(test_url)
        assert_equals(response, expected)

    def test_is_issn_in_doaj_false(self):
        response = provider.is_issn_in_doaj("invalidissn")
        assert_equals(response, False)

    def test_is_issn_in_doaj_true(self):
        zookeys_issn = "13132989"  #this one is in test setup
        response = provider.is_issn_in_doaj(zookeys_issn)
        assert_equals(response, True)

    def test_import_products(self):
        response = provider.import_products("product_id_strings", 
                {"product_id_strings": ["123456", "HTTPS://starbucks.com", "arXiv:1305.3328", "http://doi.org/10.123/ABC"]})
        expected = [('pmid', '123456'), ('url', 'HTTPS://starbucks.com'), ('arxiv', '1305.3328'), ('doi', '10.123/abc')]
        assert_equals(response, expected)

    def test_import_products_bad_providername(self):
        response = provider.import_products("nonexistant", {})
        expected = []
        assert_equals(response, expected)



class TestProviderFactory():

    TEST_PROVIDER_CONFIG = [
        ("pubmed", { "workers":1 }),
        ("wikipedia", {"workers": 3}),
        ("mendeley", {"workers": 3}),
    ]

    def test_get_all_static_meta(self):
        sm = ProviderFactory.get_all_static_meta(self.TEST_PROVIDER_CONFIG)
        expected = 'The number of citations by papers in PubMed Central'
        assert_equals(sm["pubmed:pmc_citations"]["description"], expected)

    def test_get_all_metric_names(self):
        response = ProviderFactory.get_all_metric_names(self.TEST_PROVIDER_CONFIG)
        expected = ['wikipedia:mentions', 'mendeley:country', 'pubmed:pmc_citations_reviews', 'mendeley:discipline', 'pubmed:f1000', 'mendeley:career_stage', 'pubmed:pmc_citations_editorials', 'mendeley:readers', 'pubmed:pmc_citations', 'mendeley:groups']
        assert_equals(response, expected)

    def test_get_all_metadata(self):
        md = ProviderFactory.get_all_metadata(self.TEST_PROVIDER_CONFIG)
        print md["pubmed"]
        assert_equals(md["pubmed"]['url'], 'http://pubmed.gov')

