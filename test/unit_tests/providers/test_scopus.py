from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/scopus")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_ID = "10.1371/journal.pone.0000308"

class TestScopus(ProviderTestCase):

    provider_name = "scopus"

    testitem_aliases = ("doi", TEST_ID)
    testitem_metrics = ("doi", TEST_ID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page, id=TEST_ID)
        expected = {'scopus:citations': 65}
        assert_equals(metrics_dict, expected)

    def test_provenance_url(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        provenance_url = self.provider._extract_provenance_url(good_page, id=TEST_ID)
        expected = "http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=36248970413"
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'scopus:citations': (65, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=36248970413')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics2(self):
        metrics_dict = self.provider.metrics([("doi", "10.1371/journal.pbio.0040286")])
        expected = {'scopus:citations': (106, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=34250706218')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

