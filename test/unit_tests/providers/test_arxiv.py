from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/arxiv")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestArxiv(ProviderTestCase):

    provider_name = "arxiv"

    testitem_members = "arxiv:1305.3328"
    testitem_aliases = ("arxiv", "1305.3328")
    testitem_biblio = ("arxiv", "1305.3328")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A GITHUB ID")), False)
  
    def test_members(self):
        members = self.provider.member_items({"arxiv_id_input": self.testitem_members})
        print members
        expected = [('arxiv', '1305.3328')]
        assert_equals(members, expected)

    def test_aliases(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('url', 'http://arxiv.org/abs/1305.3328')]
        assert_equals(aliases, expected)

    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio = self.provider._extract_biblio(f.read(), "1305.3328")
        expected = {'repository': 'arXiv', 'title': u'Altmetrics in the wild: Using social media to explore scholarly impact', 'year': u'2012', 'free_fulltext_url': 'http://arxiv.org/abs/1305.3328', 'authors': u'Priem, Piwowar, Hemminger', 'date': u'2012-03-20T19:46:25Z'}
        print biblio
        assert_items_equal(biblio, expected)

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'repository': 'arXiv', 'title': u'Riding the crest of the altmetrics wave: How librarians can help prepare\n  faculty for the next generation of research impact metrics', 'year': u'2013', 'free_fulltext_url': 'http://arxiv.org/abs/1305.3328', 'authors': u'Lapinski, Piwowar, Priem', 'date': u'2013-05-15T00:46:53Z'}
        assert_items_equal(biblio_dict.keys(), expected.keys())


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


    def test_provider_aliases_400(self):
        pass
    def test_provider_aliases_500(self):
        pass



