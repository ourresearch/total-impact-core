from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderFactory
from nose.tools import assert_equals, nottest
from xml.dom import minidom 

import simplejson, BeautifulSoup
import os

sampledir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/")

class Test_Provider():

    TEST_PROVIDER_CONFIG = [
        ("pubmed", { "workers":1 }),
        ("wikipedia", {"workers": 3}),
        ("mendeley", {"workers": 3}),
    ]
    
    TEST_JSON = """{"repository":{"homepage":"","watchers":7,"has_downloads":true,"fork":false,"language":"Java","has_issues":true,"has_wiki":true,"forks":0,"size":4480,"private":false,"created_at":"2008/09/29 04:26:42 -0700","name":"gtd","owner":"egonw","description":"Git-based ToDo tool.","open_issues":2,"url":"https://github.com/egonw/gtd","pushed_at":"2012/02/28 10:21:26 -0800"}}"""

    TEST_XML = open(os.path.join(sampledir, "crossref", "aliases")).read()

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
        assert_equals(set(provider_names), set(['Mendeley', 'Pubmed']))

    def test_get_providers_filters_by_aliases(self):
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG, "aliases")
        provider_names = [provider.__class__.__name__ for provider in providers]
        assert_equals(set(provider_names), set(['Pubmed', "Mendeley"]))

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
        response = provider._lookup_xml_from_dom(doc, ['title'])
        assert_equals(response, u'Sharing Detailed Research Data Is Associated with Increased Citation Rate')

    def test_lookup_xml_from_soup(self):
        page = self.TEST_XML
        doc = BeautifulSoup.BeautifulStoneSoup(page) 
        response = provider._lookup_xml_from_soup(doc, ['title'])
        assert_equals(response, u'Sharing Detailed Research Data Is Associated with Increased Citation Rate')        

    def test_extract_xml(self):
        page = self.TEST_XML
        dict_of_keylists = {
            'title' : ['doi_record', 'title'],
            'year' : ['doi_record', 'year']}

        response = provider._extract_from_xml(page, dict_of_keylists)
        assert_equals(response, {'title': u'Sharing Detailed Research Data Is Associated with Increased Citation Rate', 'year': 2007})

    def test_doi_from_url_string(self):
        test_url = "https://knb.ecoinformatics.org/knb/d1/mn/v1/object/doi:10.5063%2FAA%2Fnrs.373.1"
        expected = "10.5063/AA/nrs.373.1"
        response = provider.doi_from_url_string(test_url)
        assert_equals(response, expected)

class TestProviderFactory():

    def test_get_all_static_meta(self):
        sm = ProviderFactory.get_all_static_meta()
        assert sm["delicious:bookmarks"]["description"], sm["delicious:bookmarks"]

    def test_get_all_metadata(self):
        md = ProviderFactory.get_all_metadata()
        print md["delicious"]
        assert md["delicious"]['metrics']["bookmarks"]["description"]
        assert_equals(md["delicious"]['url'], "http://www.delicious.com")

