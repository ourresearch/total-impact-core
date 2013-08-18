from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/scopus")
SAMPLE_EXTRACT_METRICS_PAGE_FROM_DOI = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_METRICS_PAGE_FROM_BIBLIO = os.path.join(datadir, "metrics_no_doi")

TEST_ID = "10.1371/journal.pone.0000308"
TEST_BIBLIO = {"title":"Scientometrics 2.0: Toward new metrics of scholarly impact on the social Web", 
                "journal":"First Monday", 
                "first_author":"Priem"}

class TestScopus(ProviderTestCase):

    provider_name = "scopus"

    testitem_aliases = ("doi", TEST_ID)
    testitem_metrics = ("doi", TEST_ID)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE_FROM_DOI, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record_with_doi(good_page, id=TEST_ID)
        metrics_dict = self.provider._extract_metrics(relevant_record, id=TEST_ID)
        expected = {'scopus:citations': 65}
        assert_equals(metrics_dict, expected)

    def test_extract_relevant_record_with_doi(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE_FROM_DOI, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record_with_doi(good_page, id=TEST_ID)
        expected = {'issn': '19326203', 'doi': '10.1371/journal.pone.0000308', 'pubdate': '2007-03-21', 'title': 'Sharing detailed research data is associated with increased citation rate', 'vol': '2', 'inwardurl': 'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=36248970413', 'scp': '36248970413', 'doctype': 'Journal', 'citedbycount': '65', 'affiliation': '', 'abs': '', 'eid': '2-s2.0-36248970413', 'authlist': '', 'sourcetitle': 'PLoS ONE', 'issue': '3', 'page': '', 'firstauth': 'Piwowar, H.A.'}
        assert_equals(relevant_record, expected)

    def test_extract_relevant_record_with_biblio(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE_FROM_BIBLIO, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record_with_biblio(good_page, id=TEST_BIBLIO)
        expected = {'issn': '13960466', 'doi': '', 'pubdate': '2010-07-01', 'title': 'Scientometrics 2.0: Toward new metrics of scholarly impact on the social Web', 'sourcetitle': 'First Monday', 'inwardurl': 'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=77956197364', 'scp': '77956197364', 'citedbycount': '20', 'doctype': 'Journal', 'vol': '15', 'affiliation': '', 'abs': '', 'eid': '2-s2.0-77956197364', 'authlist': '', 'issue': '7', 'page': '', 'firstauth': 'Priem, J.'}
        assert_equals(relevant_record, expected)        

    def test_provenance_url(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE_FROM_DOI, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record_with_doi(good_page, id=TEST_ID)
        provenance_url = self.provider._extract_provenance_url(relevant_record, id=TEST_ID)
        expected = "http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=36248970413"
        assert_equals(provenance_url, expected)

    @http
    def test_metrics_with_bad_doi(self):
        metrics_dict = self.provider.metrics([("doi", "NOTAVALIDDOI")])
        expected = {}
        print metrics_dict
        assert_equals(metrics_dict, expected)

    @http
    def test_metrics_with_doi(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'scopus:citations': (65, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=36248970413')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_with_biblio(self):
        metrics_dict = self.provider.metrics([("biblio", TEST_BIBLIO)])
        expected = {'scopus:citations': (20, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=77956197364')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics2(self):
        metrics_dict = self.provider.metrics([("doi", "10.1371/journal.pbio.0040286")])
        expected = {'scopus:citations': (106, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=34250706218')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_case_insensitivity(self):
        metrics_dict = self.provider.metrics([("doi", "10.1017/s0022112005007494")])
        expected = {'scopus:citations': (179, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=32044436746')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

