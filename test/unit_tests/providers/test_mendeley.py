from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.api import app

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/mendeley")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE

TEST_DOI = "10.1371/journal.pcbi.1000361"

class TestMendeley(ProviderTestCase):

    provider_name = "mendeley"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_metrics = ("doi", TEST_DOI)
    testitem_biblio = ("doi", TEST_DOI)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        assert_equals(ret, {'authors': u'Shotton, Portwin, Klyne, Miles', 'journal': u'PLoS Computational Biology', 'year': 2009, 'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article'})

    def test_extract_aliases(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = self.provider._extract_aliases(f.read())
        assert_equals(aliases, [('url', u'http://dx.doi.org/10.1371/journal.pcbi.1000361'), ('title', u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article')])        

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(metrics_dict["mendeley:readers"], 50)
        assert_equals(metrics_dict["mendeley:groups"], 4)

    def test_extract_provenance_url(self):
        f = open(SAMPLE_EXTRACT_PROVENANCE_URL_PAGE, "r")
        provenance_url = self.provider._extract_provenance_url(f.read())
        assert_equals(provenance_url, "http://api.mendeley.com/research/snps-prescriptions-predict-drug-response/")

