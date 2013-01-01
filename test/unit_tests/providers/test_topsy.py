from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/topsy")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_ID = "http://total-impact.org"

class TestTopsy(ProviderTestCase):

    provider_name = "topsy"

    testitem_aliases = ("url", TEST_ID)
    testitem_metrics = ("url", TEST_ID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        expected = {'topsy:influential_tweets': 26, 'topsy:tweets': 282}
        assert_equals(metrics_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("tweets", 
            [self.testitem_aliases])
        expected = 'http://topsy.com/total-impact.org?utm_source=otter'
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'topsy:influential_tweets': (36, 'http://topsy.com/total-impact.org?utm_source=otter'), 'topsy:tweets': (358, 'http://topsy.com/total-impact.org?utm_source=otter')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_multiple_urls(self):
        metrics_dict = self.provider.metrics([("url","http://datadryad.org/handle/10255/dryad.234"), 
                                                ("url", "http://dx.doi.org/10.5061/dryad.234")])
        expected = {'topsy:tweets': (4, 'http://topsy.com/dx.doi.org/10.5061/dryad.234?utm_source=otter')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

