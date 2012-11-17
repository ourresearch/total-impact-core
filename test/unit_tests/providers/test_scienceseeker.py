from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/scienceseeker")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_DOI = "10.1016/j.cbpa.2010.06.169"

class TestScienceseeker(ProviderTestCase):

    provider_name = "scienceseeker"

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
        print metrics_dict
        expected = {'scienceseeker:blog_posts': 1}
        assert_equals(metrics_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("blog_posts", 
            [self.testitem_aliases])
        expected = 'http://scienceseeker.org/posts/?type=post&filter0=citation&modifier0=id-all&value0=10.1016/j.cbpa.2010.06.169'
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'scienceseeker:blog_posts': (1, 'http://scienceseeker.org/posts/?type=post&filter0=citation&modifier0=id-all&value0=10.1016/j.cbpa.2010.06.169')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_another(self):
        metrics_dict = self.provider.metrics([("doi", "10.1371/journal.pone.0035769")])
        expected = {'scienceseeker:blog_posts': (1, 'http://scienceseeker.org/posts/?type=post&filter0=citation&modifier0=id-all&value0=10.1371/journal.pone.0035769')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]
