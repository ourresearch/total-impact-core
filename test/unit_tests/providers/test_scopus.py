from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/scopus")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_ID = "10.1371/journal.pone.0000308"
TEST_BIBLIO = {"title":"Scientometrics 2.0: Toward new metrics of scholarly impact on the social Web", 
                "journal":"First Monday", 
                "first_author":"Priem"}
TEST_BIBLIO2 = {
                    "authors": "Quezada IM, Gianoli E", 
                    "genre": "article", 
                    "journal": "Polish Journal of Ecology", 
                    "title": "Simulated herbivory limits phenotypic responses to drought in Convolvulus demissus choisy (Convolvulaceae)", 
                    "year": "2006"
                }

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
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record(good_page, id=TEST_ID)
        metrics_dict = self.provider._extract_metrics(relevant_record, id=TEST_ID)
        expected = {'scopus:citations': 97}
        assert_equals(metrics_dict, expected)

    def test_extract_relevant_record_with_doi(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record(good_page, id=TEST_ID)
        print relevant_record
        expected = {'prism:url': 'http://api.elsevier.com/content/abstract/scopus_id:36248970413', '@_fa': 'true', 'citedby-count': '97'}
        assert_equals(relevant_record, expected)

    def test_extract_relevant_record_with_biblio(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record(good_page, id=TEST_BIBLIO)
        print relevant_record
        expected = {'prism:url': 'http://api.elsevier.com/content/abstract/scopus_id:36248970413', '@_fa': 'true', 'citedby-count': '97'}
        assert_equals(relevant_record, expected)        

    def test_provenance_url(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        relevant_record = self.provider._extract_relevant_record(good_page, id=TEST_ID)
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
    def test_metrics_with_biblio2(self):
        metrics_dict = self.provider.metrics([("biblio", TEST_BIBLIO2)])
        expected = {'scopus:citations': (7, 'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=33750324740')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics2(self):
        metrics_dict = self.provider.metrics([("doi", "10.1371/journal.pbio.0040286")])
        expected = {'scopus:citations': (113, u'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=33748598232')}
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

    @http
    def test_metrics_from_strange_doi(self):
        metrics_dict = self.provider.metrics([("doi", "10.1175/1520-0450(1994)033<0140:astmfm>2.0.co;2")])
        expected = {}
        print metrics_dict
        assert_equals(metrics_dict, expected)

    @http
    def test_metrics_from_strange_doi2(self):
        metrics_dict = self.provider.metrics([
            ("doi", "10.1670/0022-1511(2007)41[483:ADOECD]2.0.CO;2"), 
            ("biblio", {
                    "authors": "McCallum", 
                    "first_author": "McCallum", 
                    "first_page": "483", 
                    "genre": "article", 
                    "journal": "Journal of Herpetology", 
                    "number": "3", 
                    "title": "Amphibian decline or extinction? Current declines dwarf background extinction rate", 
                    "volume": "41", 
                    "year": "2007"
                })])
        expected = {'scopus:citations': (62, 'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=35148813206')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]            

    @http
    def test_metrics_many_citations_from_biblio(self):
        biblio = {
                            "authors": "Daly, Neilson, Phillips", 
                            "journal": "Journal of Applied Meteorology", 
                            "title": "A Statistical-Topographic Model for Mapping Climatological Precipitation over Mountainous Terrain", 
                            "year": "1994"
                            }

        metrics_dict = self.provider.metrics([("biblio", biblio)])
        expected = {'scopus:citations': (1091, 'http://www.scopus.com/inward/record.url?partnerID=HzOxMe3b&scp=0028552275')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    def test_provider_metrics_500(self):
        pass


