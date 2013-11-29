from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises, nottest

class TestBlog_post(ProviderTestCase):

    provider_name = "blog_post"

    testitem_aliases = ("blog_post:retractionwatch.wordpress.com", u'http://retractionwatch.wordpress.com/2012/12/11/elsevier-editorial-system-hacked-reviews-faked-11-retractions-follow/')

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("url", "https://twitter.com/researchremix/status/400821465828061184")), False)


    def test_aliases(self):
        response = self.provider.aliases([self.testitem_aliases])
        print response
        expected = [('url', u'http://retractionwatch.wordpress.com/2012/12/11/elsevier-editorial-system-hacked-reviews-faked-11-retractions-follow/')]
        assert_equals(response, expected)

    def test_provider_aliases_400(self):
        pass
    def test_provider_aliases_500(self):
        pass
