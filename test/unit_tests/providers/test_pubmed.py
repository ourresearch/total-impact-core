from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from test.utils import http
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
TEST_PMID = "16901231"

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
        assert_equals(aliases, [('pmid', '19381256')])

    def test_extract_aliases_from_pmid(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_FROM_PMID_PAGE, "r")
        aliases = self.provider._extract_aliases_from_pmid(f.read())
        assert_equals(aliases, [('doi', u'10.1371/journal.pmed.0040215')])

    def test_extract_citing_pmcids(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        pmcids = self.provider._extract_citing_pmcids(f.read())
        assert_equals(len(pmcids), 149)

    @http
    def test_aliases_from_pmid(self):
        print self.testitem_aliases
        metrics_dict = self.provider.aliases([self.testitem_aliases])
        assert_equals(set(metrics_dict), set([('doi', u'10.1089/omi.2006.10.231'), ('pmid', '16901231')]))

    @http
    def test_aliases_from_doi(self):
        metrics_dict = self.provider.aliases([("doi", TEST_DOI)])
        assert_equals(set(metrics_dict), set([('pmid', '19381256'), ('doi', '10.1371/journal.pcbi.1000361')]))

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'pubmed:pmc_citations': (12, 'http://www.ncbi.nlm.nih.gov/pubmed?linkname=pubmed_pubmed_citedin&from_uid=16901231'), 'pubmed:pmc_citations_reviews': (2, u'http://www.ncbi.nlm.nih.gov/pubmed?term=20455752 OR 18192184&cmd=DetailsSearch')}
        assert_equals(metrics_dict, expected)


