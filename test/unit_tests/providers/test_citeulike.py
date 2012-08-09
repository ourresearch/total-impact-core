from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.views import app

import os
import collections
from nose.tools import assert_equals, raises, nottest
from test.utils import http

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/citeulike")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_DOI = "10.1371/journal.pcbi.1000361"

class TestCiteulike(ProviderTestCase):

    provider_name = "citeulike"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_metrics = ("doi", TEST_DOI)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        expected = {'citeulike:bookmarks': 5}
        assert_equals(metrics_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("bookmarks", 
            [self.testitem_aliases])
        expected = 'http://www.citeulike.org/doi/10.1371/journal.pcbi.1000361'
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'citeulike:bookmarks': (59, 'http://www.citeulike.org/doi/10.1371/journal.pcbi.1000361')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

