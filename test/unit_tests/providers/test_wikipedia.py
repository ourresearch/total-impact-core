from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/wikipedia")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

TEST_DOI = "10.1371/journal.pcbi.1000361"

class TestWikipedia(ProviderTestCase):

    provider_name = "wikipedia"

    testitem_metrics = ("doi", TEST_DOI)
    testitem_aliases = ("doi", TEST_DOI)
    testitem_biblio = None
    testitem_members = None

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        ### Is there anything that wikipedia shouldn't match? 
  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        assert_equals(metrics_dict["wikipedia:mentions"], 1)

    def test_extract_metrics_empty(self):
        # now give it something with no results
        empty_page = """<?xml version="1.0"?>
                <api>
                    <query>
                        <searchinfo totalhits="0" />
                        <search></search>
                    </query>
                </api>
                """
        res = self.provider._extract_metrics(empty_page)
        assert_equals(res, {})
        
    @raises(ProviderContentMalformedError)    
    def test_extract_metrics_invalid(self):
        incorrect_doc = """this isn't the wikipedia search result page you are looking for"""
        self.provider._extract_metrics(incorrect_doc)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'wikipedia:mentions': (1, 'http://en.wikipedia.org/wiki/Special:Search?search="10.1371/journal.pcbi.1000361"&go=Go')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]


