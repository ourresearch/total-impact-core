from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/mendeley")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE

TEST_DOI = "10.1371/journal.pbio.1000056"

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
        assert_equals(metrics_dict["mendeley:discipline"], [{'id': 6, 'value': 40, 'name': 'Computer and Information Science'}, {'id': 3, 'value': 24, 'name': 'Biological Sciences'}, {'id': 23, 'value': 12, 'name': 'Social Sciences'}])
        assert_equals(metrics_dict["mendeley:career_stage"][0], {'name': 'Librarian', 'value': 22})
        assert_equals(metrics_dict["mendeley:country"][0], {'name': 'United States', 'value': 22})

    def test_extract_provenance_url(self):
        f = open(SAMPLE_EXTRACT_PROVENANCE_URL_PAGE, "r")
        provenance_url = self.provider._extract_provenance_url(f.read())
        assert_equals(provenance_url, "http://api.mendeley.com/research/snps-prescriptions-predict-drug-response/")

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'mendeley:discipline': ([{u'id': 3, u'value': 89, u'name': u'Biological Sciences'}, {u'id': 12, u'value': 7, u'name': u'Environmental Sciences'}, {u'id': 7, u'value': 4, u'name': u'Earth Sciences'}], u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:country': ([{u'name': u'Brazil', u'value': 24}, {u'name': u'United States', u'value': 23}, {u'name': u'United Kingdom', u'value': 7}], u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:career_stage': ([{u'name': u'Ph.D. Student', u'value': 31}, {u'name': u'Post Doc', u'value': 14}, {u'name': u'Student (Master)', u'value': 12}], u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:groups': (7, u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:readers': (173, u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/')}
        print metrics_dict
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 
        # can't tell more about dicsciplines etc because they are percentages and may go up or down

