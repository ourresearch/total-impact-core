from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderClientError, ProviderServerError
from totalimpact.providers import provider

from test.utils import http
from totalimpact import app, db
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/mendeley")
SAMPLE_EXTRACT_UUID_PAGE = os.path.join(datadir, "uuidlookup")
SAMPLE_EXTRACT_UUID_PAGE_NO_DOI = os.path.join(datadir, "uuidlookup_no_doi")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_BIBLIO_PAGE_OAI = os.path.join(datadir, "biblio_oai")

TEST_DOI = "10.1038/nature10658"  # matches UUID sample page

class TestNewMendeley(ProviderTestCase):

    provider_name = "mendeley_new"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_aliases_biblio_no_doi =  ("biblio", {'title': 'Scientometrics 2.0: Toward new metrics of scholarly impact on the social Web', 'first_author': 'Priem', 'journal': 'First Monday', 'number': '7', 'volume': '15', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': '2010'})
    testitem_metrics_dict = {"biblio":[{"year":2011, "authors":"sdf", "title": "Mutations causing syndromic autism define an axis of synaptic pathophysiology"}],"doi":[TEST_DOI]}
    testitem_metrics = [(k, v[0]) for (k, v) in testitem_metrics_dict.items()]
    testitem_metrics_dict_wrong_year = {"biblio":[{"year":9999, "authors":"sdf", "title": "Mutations causing syndromic autism define an axis of synaptic pathophysiology"}],"doi":[TEST_DOI]}
    testitem_metrics_wrong_year = [(k, v[0]) for (k, v) in testitem_metrics_dict_wrong_year.items()]

    def setUp(self):
        self.db = setup_postgres_for_unittests(db, app)
        ProviderTestCase.setUp(self)
        
    def tearDown(self):
        teardown_postgres_for_unittests(self.db)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    @http
    def test_metrics_doi(self):
        # at the moment this item 
        metrics_dict = self.provider.metrics([("doi", "10.1038/nature10658")])
        print metrics_dict
        expected = {'mendeley_new:countries': ({u'Canada': 2, u'United Kingdom': 5, u'Netherlands': 4, u'Portugal': 2, u'Mexico': 1, u'Finland': 1, u'France': 3, u'United States': 21, u'Austria': 2, u'Vietnam': 1, u'Germany': 4, u'China': 2, u'Japan': 4, u'Brazil': 5, u'New Zealand': 1, u'Spain': 1}, u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology'), 'mendeley_new:readers': (295, u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology')}
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 

    @http
    def test_metrics_pmid(self):
        # at the moment this item 
        metrics_dict = self.provider.metrics([("pmid", "12578738")])
        expected = {'mendeley_new:countries': ({u'United States': 1, u'Brazil': 1, u'Philippines': 1, u'Denmark': 1, u'Belgium': 1}, u'http://www.mendeley.com/research/value-data-2'), 'mendeley_new:readers': (15, u'http://www.mendeley.com/research/value-data-2')}
        print metrics_dict
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 
        # can't tell more about dicsciplines etc because they are percentages and may go up or down

    @http
    def test_metrics_arxiv(self):
        # at the moment this item 
        metrics = self.provider.metrics([("arxiv", "1203.4745")])
        print metrics
        expected = {'mendeley_new:countries': ({u'Canada': 9, u'Brazil': 9, u'Italy': 4, u'Lithuania': 1, u'France': 2, u'Republic of Singapore': 1, u'Ireland': 1, u'Argentina': 1, u'Venezuela': 1, u'Australia': 3, u'Germany': 12, u'Spain': 7, u'Ukraine': 1, u'Netherlands': 6, u'Denmark': 2, u'Finland': 1, u'United States': 27, u'Sweden': 2, u'Portugal': 1, u'Mexico': 1, u'South Africa': 4, u'United Kingdom': 17, u'Malaysia': 1, u'Austria': 1, u'Japan': 4}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley_new:readers': (198, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact')}
        assert_equals(metrics, expected)




