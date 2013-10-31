from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/vimeo")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestVimeo(ProviderTestCase):

    provider_name = "vimeo"

    testitem_aliases = ("url", "http://vimeo.com/48605764")
    testitem_metrics = ("url", "http://vimeo.com/48605764")
    testitem_biblio = ("url", "http://vimeo.com/48605764")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)
        assert_equals(self.provider.is_relevant_alias(("url", "NOT A VIMEO ID")), False)
  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read(), id=self.testitem_metrics[1])
        print metrics_dict
        assert_equals(metrics_dict["vimeo:plays"], 83)

    def test_extract_biblio_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio_dict = self.provider._extract_biblio(f.read(), self.testitem_biblio[1])
        print biblio_dict
        expected = {'repository': 'Vimeo', 'title': 'Wheat Rust Inoculation Protocol Video', 'url': 'http://vimeo.com/48605764', 'year': '2012', 'authors': 'Huang Lab', 'published_date': '2012-08-31 12:20:16'}
        assert_equals(biblio_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("github:forks", [self.testitem_aliases])
        assert_equals(provenance_url, 'http://vimeo.com/48605764')

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'vimeo:plays': (83, 'http://vimeo.com/48605764')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'repository': 'Vimeo', 'title': u'Wheat Rust Inoculation Protocol Video', 'url': u'http://vimeo.com/48605764', 'year': u'2012', 'authors': u'Huang Lab', 'published_date': u'2012-08-31 12:20:16'}
        assert_items_equal(biblio_dict.keys(), expected.keys())
        for key in ['year', 'published_date', 'title', 'url']:
            assert_equals(biblio_dict[key], expected[key])

