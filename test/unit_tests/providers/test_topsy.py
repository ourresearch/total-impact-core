from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.api import app

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/topsy")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_ID = "http://total-impact.org"

class TestTopsy(ProviderTestCase):

    provider_name = "topsy"

    testitem_metrics = ("url", TEST_ID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    @nottest  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        assert_equals(metrics_dict["wikipedia:mentions"], 1)

    @nottest  
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
        assert_equals(res["wikipedia:mentions"], 0)
        
    @nottest  
    @raises(ProviderContentMalformedError)    
    def test_extract_metrics_invalid(self):
        incorrect_doc = """this isn't the wikipedia search result page you are looking for"""
        self.provider._extract_metrics(incorrect_doc)


