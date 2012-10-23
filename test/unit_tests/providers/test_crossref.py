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
        expected = {'title': 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'journal': 'PLoS Computational Biology', 'year': 2009, 'repository': 'Public Library of Science', 'authors': 'Shotton, Portwin, Klyne, Miles'}
        print biblio
        assert_equals(biblio, expected)

    @http
    def test_get_aliases_for_id(self):
        new_aliases = self.provider._get_aliases_for_id(self.testitem_aliases[1])
        print new_aliases
        expected = [('url', 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), ('biblio', {'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'journal': u'PLoS Computational Biology', 'year': 2009, 'repository': u'Public Library of Science', 'authors': u'Shotton, Portwin, Klyne, Miles'}), ('url', u'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361')]
        assert_equals(sorted(new_aliases), sorted(expected))

    @http
    def test_biblio_elife(self):
        biblio = self.provider.biblio([("doi", "10.7554/eLife.00048")])
        expected = {'title': u'The unfolded protein response in fission yeast modulates stability of select mRNAs to maintain protein homeostasis', 'journal': u'eLife', 'year': 2012, 'repository': u'eLife Sciences Publications, Ltd.', 'authors': u'Kimmig, Diaz, Zheng, Williams, Lang, Arag\xf3n, Li, Walter'}

        print biblio
        assert_equals(biblio, expected)        

    @http
    def test_biblio_figshare(self):
        biblio = self.provider.biblio([("doi", "10.6084/m9.figshare.134")])
        expected = {'title': u'Leave One Out N15 Prediction Analysis', 'year': u'2011', 'repository': u'Figshare', 'authors': u'Antony Williams'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio_dryad(self):
        biblio = self.provider.biblio([("doi", "10.5061/dryad.3td2f")])
        expected = {'title': u'Data from: Public sharing of research datasets: a pilot study of associations', 'year': u'2011', 'repository': u'Dryad Digital Repository', 'authors': u'Piwowar, Chapman'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio_pangaea(self):
        biblio = self.provider.biblio([("doi", "/10.1594/PANGAEA.339110")])
        expected = {'title': u"Audio record of a 'singing iceberg' from the Weddell Sea, Antarctica, supplement to: M\xfcller, Christian; Schlindwein, Vera; Eckstaller, Alfons; Miller, Heinz (2005): Singing Icebergs. Science, 310, 12", 'year': u'2005', 'repository': u'PANGAEA - Data Publisher for Earth & Environmental Science', 'authors': u'M\xfcller, Schlindwein, Eckstaller, Miller'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio_science(self):
        biblio = self.provider.biblio([("doi", "10.1126/science.169.3946.635")])
        expected = {'title': u'The Structure of Ordinary Water: New data and interpretations are yielding new insights into this fascinating substance', 'journal': u'Science', 'year': 1970, 'repository': u'American Association for the Advancement of Science', 'authors': u'Frank'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio(self):
        biblio = self.provider.biblio([self.testitem_biblio])
        expected = {'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'journal': u'PLoS Computational Biology', 'year': 2009, 'repository': u'Public Library of Science', 'authors': u'Shotton, Portwin, Klyne, Miles'}
        print biblio
        assert_equals(biblio, expected)        

    @http
    def test_aliases_elife(self):
        aliases = self.provider.aliases([("doi", "10.7554/eLife.00048")])
        expected = [('biblio', {'title': u'The unfolded protein response in fission yeast modulates stability of select mRNAs to maintain protein homeostasis', 'journal': u'eLife', 'year': 2012, 'repository': u'eLife Sciences Publications, Ltd.', 'authors': u'Kimmig, Diaz, Zheng, Williams, Lang, Arag\xf3n, Li, Walter'}), ('url', 'http://dx.doi.org/10.7554/eLife.00048'), ('url', u'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3470409/')]

        print aliases
        assert_equals(sorted(aliases), sorted(expected))

    @http
    def test_aliases_elife_figure(self):
        aliases = self.provider.aliases([("doi", "10.7554/eLife.00048.002")])
        expected = [('biblio', {'repository': u'eLife Sciences Publications, Ltd.'}), ('url', 'http://dx.doi.org/10.7554/eLife.00048.002'), ('url', u'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3470409/')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))
