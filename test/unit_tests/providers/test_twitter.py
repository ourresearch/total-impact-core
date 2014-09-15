from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises, nottest

class TestTwitter(ProviderTestCase):

    provider_name = "twitter"

    testitem_members = "jasonpriem"
    testitem_aliases = ("url", "http://twitter.com/jasonpriem")
    testitem_metrics = ("url", "http://twitter.com/jasonpriem")
    testitem_biblio = ("url", "http://twitter.com/jasonpriem")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("url", "https://twitter.com/researchremix/status/400821465828061184")), False)


    def test_screen_name(self):
        # ensure that it matches an appropriate ids
        response = self.provider.screen_name(self.testitem_aliases[1])
        assert_equals(response, "jasonpriem")

  
    def test_extract_members_success(self):        
        members = self.provider.member_items(self.testitem_members)
        print members
        expected = [('url', 'http://twitter.com/jasonpriem')]
        assert_equals(members, expected)


    def test_extract_members_success_with_at(self):        
        members = self.provider.member_items("@" + self.testitem_members)
        print members
        expected = [('url', 'http://twitter.com/jasonpriem')]
        assert_equals(members, expected)


    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("twitter:lists", [self.testitem_aliases])
        assert_equals(provenance_url, 'https://twitter.com/jasonpriem/memberships')

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'twitter:lists': (215, 'https://twitter.com/jasonpriem/memberships'), 'twitter:followers': (3069, 'https://twitter.com/jasonpriem/followers')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_bad_twitttername(self):
        metrics_dict = self.provider.metrics([("url", "http://twitter.com/researchremix22")])
        print metrics_dict
        expected = {}
        assert_equals(metrics_dict, expected)


    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'account': u'@jasonpriem', 'description': u'Info Science PhD student, ImpactStory co-founder. I care hard about #OA, #altmetrics, and bringing scholarly communication into the age of the web.', 'repository': 'Twitter', 'title': u'@jasonpriem', 'url': u'http://twitter.com/jasonpriem', 'created_at': u'Mon Jun 16 19:19:43 +0000 2008', 'is_account': True, 'authors': u'Jason Priem', 'genre': 'account'}
        assert_items_equal(biblio_dict.keys(), expected.keys())
        for key in expected.keys():
            assert_equals(biblio_dict[key], expected[key])

    # not relevant given library approach

    def test_provider_member_items_400(self):
        pass
    def test_provider_member_items_500(self):
        pass
    def test_provider_member_items_empty(self):
        pass
    def test_provider_member_items_nonsense_txt(self):
        pass
    def test_provider_member_items_nonsense_xml(self):
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

    def test_provider_biblio_400(self):
        pass
    def test_provider_biblio_500(self):
        pass
