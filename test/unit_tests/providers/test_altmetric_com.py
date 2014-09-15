from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
import pprint
from nose.tools import assert_equals, assert_items_equal, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/altmetric_com")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_METRICS_PAGE_EXTENDED = os.path.join(datadir, "sample.json")

TEST_ID = "10.1101/gr.161315.113"

class TestAltmetric_Com(ProviderTestCase):

    provider_name = "altmetric_com"

    testitem_aliases = ("doi", TEST_ID)
    testitem_metrics = ("doi", TEST_ID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_aliases_success(self):
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        good_page = f.read()
        aliases_list = self.provider._extract_aliases(good_page)
        expected = [('altmetric_com', '1870595')]
        assert_equals(aliases_list, expected)

    def test_extract_metrics_success_via_fetch(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE_EXTENDED, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics_via_fetch(good_page)
        print metrics_dict.keys()
        expected_keys = ['altmetric_com:news', 'altmetric_com:news_names', 'altmetric_com:impressions', 'altmetric_com:demographics', 'altmetric_com:tweeter_followers', 'altmetric_com:tweets', 'altmetric_com:unique_tweeters', 'altmetric_com:unique_news']
        assert_items_equal(expected_keys, metrics_dict.keys())
        assert_equals(metrics_dict["altmetric_com:news"], 33)
        assert_equals(metrics_dict["altmetric_com:unique_news"], 22)
        assert_equals(metrics_dict["altmetric_com:tweets"], 2235)
        assert_equals(metrics_dict["altmetric_com:tweeter_followers"][0:3], [['busterzdad', 16], ['ggsimpsonrna', 129], ['JohnNosta', 17738]])
        assert_equals(metrics_dict["altmetric_com:impressions"], 5966059)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("tweets", 
            [self.testitem_aliases])
        expected = ""
        assert_equals(provenance_url, expected)

        provenance_url = self.provider.provenance_url("tweets", 
            [self.testitem_aliases, ("altmetric_com", "1870595")])
        expected = 'http://www.altmetric.com/details.php?citation_id=1870595&src=impactstory.org'
        assert_equals(provenance_url, expected)

    @http
    def test_aliases(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('altmetric_com', '1870595')]
        assert_equals(aliases, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([("altmetric_com", "1870595")])
        expected = {'altmetric_com:gplus_posts': (1, 'http://www.altmetric.com/details.php?citation_id=1870595&src=impactstory.org'), 'altmetric_com:facebook_posts': (1, 'http://www.altmetric.com/details.php?citation_id=1870595&src=impactstory.org'), 'altmetric_com:tweets': (55, 'http://www.altmetric.com/details.php?citation_id=1870595&src=impactstory.org'), 'altmetric_com:blog_posts': (2, 'http://www.altmetric.com/details.php?citation_id=1870595&src=impactstory.org')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    def test_provider_aliases_400(self):
        pass
    def test_provider_aliases_500(self):
        pass

    def test_provider_metrics_400(self):
        pass
    def test_provider_metrics_500(self):
        pass
    def test_provider_metrics_empty(self):
        pass
    def test_provider_metrics_nonsense_txt(self):
        pass
    def test_provider_metrics_nonsense_xml(self):
        pass


