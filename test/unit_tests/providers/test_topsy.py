from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/topsy")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_METRICS_SITE_PAGE = os.path.join(datadir, "metrics_site")

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

    def test_extract_metrics_site_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_SITE_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        expected = {'topsy:tweets': 221}
        assert_equals(metrics_dict, expected)


    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("tweets", 
            [self.testitem_aliases])
        expected = 'http://topsy.com/trackback?url=http%3A//total-impact.org&window=a'
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'topsy:influential_tweets': (7, 'http://topsy.com/trackback?url=http%3A//total-impact.org&window=a'), 'topsy:tweets': (46, 'http://topsy.com/trackback?url=http%3A//total-impact.org&window=a')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics2(self):
        metrics_dict = self.provider.metrics([("url", "http://researchremix.wordpress.com/2011/08/10/personal")])
        expected = {'topsy:influential_tweets': (1, 'http://topsy.com/trackback?url=http%3A//researchremix.wordpress.com/2011/08/10/personal/&window=a'), 'topsy:tweets': (18, 'http://topsy.com/trackback?url=http%3A//researchremix.wordpress.com/2011/08/10/personal/&window=a')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

        #now with trailing slawh
        metrics_dict2 = self.provider.metrics([("url", "http://researchremix.wordpress.com/2011/08/10/personal/")])
        assert_items_equal(metrics_dict, metrics_dict2)


    @http
    def test_metrics_blog(self):
        metrics_dict = self.provider.metrics([("blog", "http://retractionwatch.wordpress.com")])
        expected = {'topsy:tweets': (8639, 'http://topsy.com/s?q=site%3Aretractionwatch.wordpress.com&window=a')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_different_urls(self):
        metrics_dict = self.provider.metrics([("url","http://datadryad.org/handle/10255/dryad.234"), 
                                                ("url", "http://dx.doi.org/10.5061/dryad.234")])
        expected = {'topsy:tweets': (5, 'http://topsy.com/trackback?url=http%3A//dx.doi.org/10.5061/dryad.234&window=a')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_top_tweeted_urls_site(self):
        response = self.provider.top_tweeted_urls("http://blog.impactstory.org", number_to_return=5)
        print response
        expected = [u'http://blog.impactstory.org/2013/09/27/impactstory-awarded-300k-nsf-grant/',
                 u'http://blog.impactstory.org/2013/01/18/github/',
                 u'http://blog.impactstory.org/2013/06/17/sloan/',
                 u'http://blog.impactstory.org/2013/07/04/impactstory-sloan-grant-proposal-details/',
                 u'http://blog.impactstory.org/2013/06/17/impact-profiles/']
        #assert_equals(response, expected)

    @http
    def test_top_tweeted_urls_tweets(self):
        response = self.provider.top_tweeted_urls("impactstory", "twitter_account", number_to_return=10)
        print response
        expected = [u'http://blog.impactstory.org/2013/09/27/impactstory-awarded-300k-nsf-grant/',
                 u'http://blog.impactstory.org/2013/01/18/github/',
                 u'http://blog.impactstory.org/2013/06/17/sloan/',
                 u'http://blog.impactstory.org/2013/07/04/impactstory-sloan-grant-proposal-details/',
                 u'http://blog.impactstory.org/2013/06/17/impact-profiles/']
        #assert_equals(response, expected)        

    @http
    def test_top_tweeted_urls_tweets(self):
        response = self.provider.top_tweeted_urls("jasonpriem", "tweets_about", number_to_return=10)
        print response
        expected = [u'http://blog.impactstory.org/2013/09/27/impactstory-awarded-300k-nsf-grant/',
                 u'http://blog.impactstory.org/2013/01/18/github/',
                 u'http://blog.impactstory.org/2013/06/17/sloan/',
                 u'http://blog.impactstory.org/2013/07/04/impactstory-sloan-grant-proposal-details/',
                 u'http://blog.impactstory.org/2013/06/17/impact-profiles/']
        #assert_equals(response, expected) 
