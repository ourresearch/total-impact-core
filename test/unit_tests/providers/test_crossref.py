from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/crossref")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

TEST_DOI = "10.1371/journal.pcbi.1000361"

class TestCrossRef(ProviderTestCase):

    provider_name = "crossref"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_biblio = ("doi", TEST_DOI)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "NOT A CROSSREF ID")), False)
  
    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio = self.provider._extract_biblio(f.read())
        expected = {'authors': 'Piwowar, Day, Fridsma', 'journal': u'PLoS ONE', 'title': u'Sharing Detailed Research Data Is Associated with Increased Citation Rate', 'year': 2007}
        print biblio
        assert_equals(biblio, expected)

    @http
    def test_get_aliases_for_id(self):
        new_aliases = self.provider._get_aliases_for_id(self.testitem_aliases[1])
        print new_aliases
        expected = [('url', 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), 
            ('biblio', {'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'authors': u'Shotton, Portwin, Klyne, Miles', 'journal': u'PLoS Comput Biol', 'year': 2009}), 
            ('url', u'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361')]
        assert_equals(sorted(new_aliases), sorted(expected))

    @http
    def test_biblio_elife(self):
        biblio = self.provider.biblio([("doi", "10.7554/eLife.00048")])
        expected = {'authors': u'Kimmig, Diaz, Zheng, Williams, Lang, Arag\xf3n, Li, Walter', 'title': u'The unfolded protein response in fission yeast modulates stability of select mRNAs to maintain protein homeostasis', 'journal': u'eLife', 'year': 2012}
        print biblio
        assert_equals(biblio, expected)        

    @http
    def test_biblio(self):
        biblio = self.provider.biblio([self.testitem_biblio])
        expected = {'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'authors': u'Shotton, Portwin, Klyne, Miles', 'journal': u'PLoS Comput Biol', 'year': 2009}
        print biblio
        assert_equals(biblio, expected)        

    @http
    def test_aliases_elife(self):
        aliases = self.provider.aliases([("doi", "10.7554/eLife.00048")])
        expected = [('biblio', {'title': u'The unfolded protein response in fission yeast modulates stability of select mRNAs to maintain protein homeostasis', 'journal': u'eLife', 'authors': u'Kimmig, Diaz, Zheng, Williams, Lang, Arag\xf3n, Li, Walter', 'year': 2012}), 
            ('url', 'http://dx.doi.org/10.7554/eLife.00048'), 
            ('url', u'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3470409/')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))

    @http
    def test_aliases_elife_figure(self):
        aliases = self.provider.aliases([("doi", "10.7554/eLife.00048.002")])
        expected = [('url', 'http://dx.doi.org/10.7554/eLife.00048.002'), ('url', u'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3470409/')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))
