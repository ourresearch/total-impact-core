from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/pubmed")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_FROM_DOI_PAGE = os.path.join(datadir, "aliases_from_doi")
SAMPLE_EXTRACT_ALIASES_FROM_PMID_PAGE = os.path.join(datadir, "aliases_from_pmid")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE

TEST_DOI = "10.1371/journal.pcbi.1000361"
TEST_PMID = "22855908"

class TestPubmed(ProviderTestCase):

    provider_name = "pubmed"

    testitem_aliases = ("pmid", TEST_PMID)
    testitem_metrics = ("pmid", TEST_PMID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    def test_extract_aliases_from_doi(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_FROM_DOI_PAGE, "r")
        aliases = self.provider._extract_aliases_from_doi(f.read())
        assert_equals(aliases, [('pmid', 19381256)])

    def test_extract_aliases_from_pmid(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_FROM_PMID_PAGE, "r")
        aliases = self.provider._extract_aliases_from_pmid(f.read())
        assert_equals(aliases, [('doi', u'10.1371/journal.pmed.0040215')])

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(metrics_dict["pubmed:pmc_citations"], 149)

