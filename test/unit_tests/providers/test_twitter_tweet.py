from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises, nottest

class TestTwitter_Tweet(ProviderTestCase):

    provider_name = "twitter_tweet"

    testitem_biblio = ("url", "https://twitter.com/researchremix/status/400821465828061184")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_biblio), True)

        assert_equals(self.provider.is_relevant_alias(("url", "https://twitter.com/researchremix")), False)


    def test_screen_name(self):
        # ensure that it matches an appropriate ids
        response = self.provider.screen_name(self.testitem_biblio[1])
        assert_equals(response, "researchremix")

  
    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'embed': u'<blockquote class="twitter-tweet" data-cards="hidden"><p>The FIRST Act Is the Last Open Access Reform We&#39;d Ever Want <a href="https://t.co/CzALjCncyJ">https://t.co/CzALjCncyJ</a> <a href="https://twitter.com/search?q=%23openaccess&amp;src=hash">#openaccess</a></p>&mdash; Heather Piwowar (@researchremix) <a href="https://twitter.com/researchremix/statuses/400821465828061184">November 14, 2013</a></blockquote>\n<script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>', 'authors': u'Heather Piwowar', 'repository': 'Twitter', 'title': u'@researchremix'}
        assert_items_equal(biblio_dict.keys(), expected.keys())
        for key in expected.keys():
            assert_equals(biblio_dict[key], expected[key])

    # not relevant given library approach
    def test_provider_biblio_400(self):
        pass
    def test_provider_biblio_500(self):
        pass
