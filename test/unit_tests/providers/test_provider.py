from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderFactory
from nose.tools import assert_equals, nottest
from xml.dom import minidom 

import simplejson, BeautifulSoup
import os

sampledir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/")

class Test_Provider():

    TEST_PROVIDER_CONFIG = {
        "wikipedia": {},
        "mendeley": {}
    }
    
    TEST_JSON = """{"repository":{"homepage":"","watchers":7,"has_downloads":true,"fork":false,"language":"Java","has_issues":true,"has_wiki":true,"forks":0,"size":4480,"private":false,"created_at":"2008/09/29 04:26:42 -0700","name":"gtd","owner":"egonw","description":"Git-based ToDo tool.","open_issues":2,"url":"https://github.com/egonw/gtd","pushed_at":"2012/02/28 10:21:26 -0800"}}"""

    TEST_XML = open(os.path.join(sampledir, "crossref", "aliases")).read()

    def test_get_provider(self):
        provider = ProviderFactory.get_provider("wikipedia")
        assert_equals(provider.__class__.__name__, "Wikipedia")
        
    def test_get_providers(self):
        providers = ProviderFactory.get_providers(self.TEST_PROVIDER_CONFIG)
        provider_names = [provider.__class__.__name__ for provider in providers]
        assert_equals(set(provider_names), set(['Mendeley', 'Wikipedia']))

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
        assert_equals(response, {'title': u'Sharing Detailed Research Data Is Associated with Increased Citation Rate', 'year': u'2007'})        
