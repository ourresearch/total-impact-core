from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/webpage")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")


class TestWebpage(ProviderTestCase):

    provider_name = "webpage"

    testitem_aliases = ("url", "http://nescent.org")
    testitem_biblio = ("url", "http://nescent.org")

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A GITHUB ID")), False)
  
    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        expected = {'h1': u'WELCOME', 'title': u'NESCent: The National Evolutionary Synthesis Center'}
        assert_equals(ret, expected)
