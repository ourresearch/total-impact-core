from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/figshare")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestFigshare(ProviderTestCase):

    provider_name = "figshare"

    testitem_aliases = ("doi", "10.6084/m9.figshare.92393")
    testitem_metrics = ("doi", "10.6084/m9.figshare.92393")
    testitem_biblio = ("doi", "10.6084/m9.figshare.92393")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A FIGSHARE ID")), False)
  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read(), id="10.6084/m9.figshare.92393")
        print metrics_dict
        assert_equals(metrics_dict["figshare:downloads"], 19)

    def test_extract_biblio_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio_dict = self.provider._extract_biblio(f.read(), id="10.6084/m9.figshare.92393")
        print biblio_dict
        expected = {'url': 'http://dx.doi.org/10.6084/m9.figshare.92393', 'title': 'Gaussian Job Archive for B2(2-)', 'year': '2012', 'authors': 'Rzepa, Harvey'}
        assert_equals(biblio_dict, expected)

    def test_extract_alias_success(self):
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases_dict = self.provider._extract_aliases(f.read(), id="10.6084/m9.figshare.92393")
        print aliases_dict
        expected = [('url', 'http://dx.doi.org/10.6084/m9.figshare.92393'), ('title', 'Gaussian Job Archive for B2(2-)')]
        assert_equals(aliases_dict, expected)

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("figshare:downloads", [self.testitem_aliases])
        expected = 'http://dx.doi.org/10.6084/m9.figshare.92393'
        assert_equals(provenance_url, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'figshare:downloads': (19, 'http://dx.doi.org/10.6084/m9.figshare.92393')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'url': 'http://dx.doi.org/10.6084/m9.figshare.92393', 'title': 'Gaussian Job Archive for B2(2-)', 'year': '2012', 'authors': 'Rzepa, Harvey'}
        assert_equals(biblio_dict, expected)


