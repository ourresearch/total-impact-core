from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/youtube")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestYoutube(ProviderTestCase):

    provider_name = "youtube"

    testitem_aliases = ("url", "http://www.youtube.com/watch?v=d39DL4ed754")
    testitem_metrics = ("url", "http://www.youtube.com/watch?v=d39DL4ed754")
    testitem_biblio = ("url", "http://www.youtube.com/watch?v=d39DL4ed754")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)
        assert_equals(self.provider.is_relevant_alias(("url", "NOT A YOUTUBE ID")), False)
  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        print metrics_dict
        assert_equals(metrics_dict["youtube:views"], 113)

    def test_extract_biblio_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio_dict = self.provider._extract_biblio(f.read(), self.testitem_biblio[1])
        print biblio_dict
        expected = {'channel_title': 'ImpactStory', 'repository': 'YouTube', 'title': 'Y Combinator video outtakes', 'url': 'http://www.youtube.com/watch?v=d39DL4ed754', 'published_date': '2013-10-15T21:48:48.000Z', 'year': '2013'}
        assert_equals(biblio_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("github:forks", [self.testitem_aliases])
        assert_equals(provenance_url, 'http://www.youtube.com/watch?v=d39DL4ed754')

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'youtube:views': (123, 'http://www.youtube.com/watch?v=d39DL4ed754'), 'youtube:likes': (3, 'http://www.youtube.com/watch?v=d39DL4ed754')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'channel_title': 'ImpactStory', 'repository': 'YouTube', 'title': 'Y Combinator video outtakes', 'url': 'http://www.youtube.com/watch?v=d39DL4ed754', 'published_date': '2013-10-15T21:48:48.000Z', 'year': '2013'}
        assert_items_equal(biblio_dict.keys(), expected.keys())
        for key in ['year', 'published_date', 'title', 'url']:
            assert_equals(biblio_dict[key], expected[key])

