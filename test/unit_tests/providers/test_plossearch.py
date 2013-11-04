from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/plossearch")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

class TestPlossearch(ProviderTestCase):

    provider_name = "plossearch"

    testitem_aliases = ("url", "http://hdl.handle.net/10255/dryad.235")
    testitem_metrics = ("url", "http://hdl.handle.net/10255/dryad.235")

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        expected = {'plossearch:mentions': 1}
        assert_equals(metrics_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("tweets", 
            [self.testitem_aliases])
        expected = 'http://www.plosone.org/search/advanced?queryTerm=&unformattedQuery=everything:"hdl.handle.net%2F10255%2Fdryad.235"'
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'plossearch:mentions': (2, 'http://www.plosone.org/search/advanced?queryTerm=&unformattedQuery=everything:"hdl.handle.net%2F10255%2Fdryad.235"')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_multiple_urls(self):
        metrics_dict = self.provider.metrics([("url","http://dx.doi.org/10.5061/dryad.234"), 
                                                ("doi", "10.5061/dryad.234"), 
                                                ("url","http://hdl.handle.net/10255/dryad.235")])
        expected = {'plossearch:mentions': (2, 'http://www.plosone.org/search/advanced?queryTerm=&unformattedQuery=everything:"hdl.handle.net%2F10255%2Fdryad.235"')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]


