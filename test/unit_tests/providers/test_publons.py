from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/publons")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestPublons(ProviderTestCase):

    provider_name = "publons"

    testitem_members = "https://publons.com/author/13201/iain-hrynaszkiewicz"
    testitem_metrics = ("url", "https://publons.com/review/182/")
    testitem_aliases = ("url", "https://publons.com/review/182/")
    testitem_biblio = ("url", "https://publons.com/review/182/")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A PUBLONS ID")), False)
  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        print metrics_dict
        assert_equals(metrics_dict["publons:views"], 13)

    def test_extract_members_success(self):        
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
        members = self.provider._extract_members(f.read(), self.testitem_members)
        expected = [('url', 'https://publons.com/r/182/')]
        assert_equals(expected, members)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("publons:views", [self.testitem_aliases])
        assert_equals(provenance_url, "https://publons.com/review/182/")

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'publons:views': (13, 'https://publons.com/review/182/')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_aliases(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('doi', u'10.7287/peerj.175v0.1/reviews/2')]
        assert_equals(expected, aliases)

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'create_date': u'2013-04-28', 'authors': u'Hrynaszkiewicz', 'repository': 'Publons', 'title': u'Data reuse and the open data citation advantage', 'journal': u'PeerJ', 'genre': 'peer review', 'year': u'2013', 'review_type': u'Pre Publication', 'review_url': u'https://peerj.com/articles/175v0.1/reviews/2/'}
        assert_items_equal(biblio_dict.keys(), expected.keys())
        for key in ["authors", "title", "create_date", "year"]:
            assert_equals(biblio_dict[key], expected[key])

    @http
    def test_members(self):
        members = self.provider.member_items(self.testitem_members)
        print members
        expected = [('url', 'https://publons.com/r/182/')]
        for member in expected:
            assert(member in members)


