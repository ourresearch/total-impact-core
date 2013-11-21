from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/wordpresscom")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestWordpresscom(ProviderTestCase):

    provider_name = "wordpresscom"

    testitem_members = "http://retractionwatch.wordpress.com"
    testitem_aliases = ("blog", "http://retractionwatch.wordpress.com")
    testitem_metrics = ("blog", "http://retractionwatch.wordpress.com")
    testitem_biblio = ("blog", "http://retractionwatch.wordpress.com")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A WORDPRESS ID")), False)
  

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("github:forks", [self.testitem_aliases])
        assert_equals(provenance_url, 'http://retractionwatch.wordpress.com')


    def test_members(self):
        response = self.provider.member_items(self.testitem_members)
        print response
        expected = [('blog', 'http://retractionwatch.wordpress.com')]
        assert_equals(response, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'wordpresscom:subscribers': (735, 'http://retractionwatch.wordpress.com')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'url': 'http://retractionwatch.wordpress.com', 'description': u'Tracking retractions as a window into the scientific process', 'title': u'Retraction Watch'}
        assert_equals(biblio_dict.keys(), expected.keys())
        for key in ["url", "title", "description"]:
            assert_equals(biblio_dict[key], expected[key])

    # not relevant given library approach

    def test_provider_member_items_400(self):
        pass
    def test_provider_member_items_500(self):
        pass
    def test_provider_member_items_empty(self):
        pass
    def test_provider_member_items_nonsense_txt(self):
        pass
    def test_provider_member_items_nonsense_xml(self):
        pass

    def test_provider_aliases_400(self):
        pass
    def test_provider_aliases_500(self):
        pass

