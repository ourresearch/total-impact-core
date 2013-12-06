from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/figshare")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestFigshare(ProviderTestCase):

    provider_name = "figshare"

    testitem_members = "http://figshare.com/authors/schamberlain/96554"
    testitem_aliases = ("doi", "10.6084/m9.figshare.92393")
    testitem_metrics = ("doi", "10.6084/m9.figshare.92393")
    testitem_biblio = ("doi", "10.6084/m9.figshare.865731")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A FIGSHARE ID")), False)
  
    def test_extract_biblio_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio_dict = self.provider._extract_biblio(f.read(), id="10.6084/m9.figshare.92393")
        print biblio_dict
        expected = {'genre': 'dataset', 'title': 'Gaussian Job Archive for B2(2-)', 'year': 2012, 'repository': 'figshare', 'published_date': '14:13, Jun 15, 2012'}
        assert_equals(biblio_dict, expected)


    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read(), id="10.6084/m9.figshare.92393")
        print metrics_dict
        assert_equals(metrics_dict["figshare:downloads"], 19)

    def test_extract_members_success(self):
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
        response = self.provider._extract_members(f.read())
        print response
        expected = [('doi', '10.6084/m9.figshare.806563'), ('doi', '10.6084/m9.figshare.806423'), ('doi', '10.6084/m9.figshare.803123'), ('doi', '10.6084/m9.figshare.791569'), ('doi', '10.6084/m9.figshare.758498'), ('doi', '10.6084/m9.figshare.757866'), ('doi', '10.6084/m9.figshare.739343'), ('doi', '10.6084/m9.figshare.729248'), ('doi', '10.6084/m9.figshare.719786'), ('doi', '10.6084/m9.figshare.669696')]
        assert_equals(response, expected)

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
        expected = {'genre': 'slides', 'title': u'Open Science', 'year': 2013, 'repository': 'figshare', 'published_date': u'03:41, Dec 03, 2013'}
        assert_equals(biblio_dict, expected)

    @http
    def test_alias(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('url', u'http://figshare.com/articles/Gaussian_Job_Archive_for_B2(2-)/92393')]
        assert_equals(sorted(aliases), sorted(expected))

    @http
    def test_members(self):
        members = self.provider.member_items(self.testitem_members)
        print members
        expected = [('doi', u'10.6084/m9.figshare.806563'), ('doi', u'10.6084/m9.figshare.806423'), ('doi', u'10.6084/m9.figshare.803123'), ('doi', u'10.6084/m9.figshare.791569'), ('doi', u'10.6084/m9.figshare.758498'), ('doi', u'10.6084/m9.figshare.757866'), ('doi', u'10.6084/m9.figshare.739343'), ('doi', u'10.6084/m9.figshare.729248'), ('doi', u'10.6084/m9.figshare.719786'), ('doi', u'10.6084/m9.figshare.669696'), ('doi', u'10.6084/m9.figshare.106915'), ('doi', u'10.6084/m9.figshare.97222'), ('doi', u'10.6084/m9.figshare.97221'), ('doi', u'10.6084/m9.figshare.97215'), ('doi', u'10.6084/m9.figshare.94296'), ('doi', u'10.6084/m9.figshare.94295'), ('doi', u'10.6084/m9.figshare.94219'), ('doi', u'10.6084/m9.figshare.94218'), ('doi', u'10.6084/m9.figshare.94217'), ('doi', u'10.6084/m9.figshare.94216'), ('doi', u'10.6084/m9.figshare.94090'), ('doi', u'10.6084/m9.figshare.94089'), ('doi', u'10.6084/m9.figshare.94030'), ('doi', u'10.6084/m9.figshare.91145'), ('doi', u'10.6084/m9.figshare.90832')]
        for expected_item in expected:
            assert expected_item in members

    @http
    def test_provider_import(self):
        tabs_input = {"account_name": "http://figshare.com/authors/schamberlain/96554", "standard_dois_input": "10.6084/m9.figshare.92393\nhttps://doi.org/10.6084/m9.figshare.865731"}
        members = provider.import_products("figshare", tabs_input)
        print members
        expected = [('doi', '10.6084/m9.figshare.92393'), ('doi', '10.6084/m9.figshare.865731'), ('doi', u'10.6084/m9.figshare.806563'), ('doi', u'10.6084/m9.figshare.806423'), ('doi', u'10.6084/m9.figshare.803123'), ('doi', u'10.6084/m9.figshare.791569'), ('doi', u'10.6084/m9.figshare.758498'), ('doi', u'10.6084/m9.figshare.757866'), ('doi', u'10.6084/m9.figshare.739343'), ('doi', u'10.6084/m9.figshare.729248'), ('doi', u'10.6084/m9.figshare.719786'), ('doi', u'10.6084/m9.figshare.669696'), ('doi', u'10.6084/m9.figshare.106915'), ('doi', u'10.6084/m9.figshare.97222'), ('doi', u'10.6084/m9.figshare.97221'), ('doi', u'10.6084/m9.figshare.97215'), ('doi', u'10.6084/m9.figshare.94296'), ('doi', u'10.6084/m9.figshare.94295'), ('doi', u'10.6084/m9.figshare.94219'), ('doi', u'10.6084/m9.figshare.94218'), ('doi', u'10.6084/m9.figshare.94217'), ('doi', u'10.6084/m9.figshare.94216'), ('doi', u'10.6084/m9.figshare.94090'), ('doi', u'10.6084/m9.figshare.94089'), ('doi', u'10.6084/m9.figshare.94030'), ('doi', u'10.6084/m9.figshare.91145'), ('doi', u'10.6084/m9.figshare.90832')]
        for member in expected:
            assert(member in members)

