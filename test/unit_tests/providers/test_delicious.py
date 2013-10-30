from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/delicious")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_ID = "http://total-impact.org/"
TEST_ID2 = "http://cas-csid.cas.unt.edu/?p=3575"

class TestDelicious(ProviderTestCase):

    provider_name = "delicious"

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
        expected = {'delicious:bookmarks': 65}
        assert_equals(metrics_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("bookmarks", 
            [self.testitem_aliases])
        expected = "http://delicious.com/link/2d6bf502d610eaa99db37fada1957a95"
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'delicious:bookmarks': (75, 'http://delicious.com/link/2d6bf502d610eaa99db37fada1957a95')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics2(self):
        metrics_dict = self.provider.metrics([("url", TEST_ID2)])
        expected = {'delicious:bookmarks': (3, 'http://delicious.com/link/41ce360e970852cc77349af2615c9d02')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]
