from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/pmc")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "monthly_download")

TEST_PMID = "23066504"

class TestPmc(ProviderTestCase):

    provider_name = "pmc"

    testitem_aliases = ("pmid", TEST_PMID)
    testitem_metrics = ("pmid", TEST_PMID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page, id="222")
        print metrics_dict
        expected = {'pmc:unique_ip': 514, 'pmc:pdf_downloads': 230, 'pmc:fulltext_views': 606, 'pmc:figure_views': 9}
        assert_equals(metrics_dict, expected)

    def test_provider_metrics_500(self):
        pass  # Not applicable

    def test_provider_metrics_400(self):
        pass  # Not applicable

    @http
    @nottest
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'scienceseeker:blog_posts': (1, 'http://scienceseeker.org/posts/?type=post&filter0=citation&modifier0=id-all&value0=10.1016/j.cbpa.2010.06.169')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

