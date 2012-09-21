from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/plosalm")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")

TEST_DOI = "10.1371/journal.pcbi.1000361"

class TestPlosalm(ProviderTestCase):

    provider_name = "plosalm"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_metrics = ("doi", TEST_DOI)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_provenance_url(self):
        # ensure that it matches an appropriate ids
        response = self.provider.provenance_url("plosalm:html_views", [self.testitem_aliases])
        assert_equals(response, "http://dx.doi.org/10.1371/journal.pcbi.1000361")

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        expected = {'plosalm:pmc_supp-data': 15, 'plosalm:html_views': 11856, 'plosalm:pmc_abstract': 96, 'plosalm:pmc_unique-ip': 856, 'plosalm:scopus': 26, 'plosalm:pdf_views': 1134, 'plosalm:pmc_pdf': 257, 'plosalm:pmc_full-text': 896, 'plosalm:pmc_figure': 70, 'plosalm:pubmed_central': 13, 'plosalm:crossref': 14}
        assert_equals(metrics_dict, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {u'plosalm:pmc_supp-data': (15, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), 'plosalm:html_views': (12198, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:scopus': (26, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:pmc_unique-ip': (900, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), 'plosalm:pdf_views': (1174, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:pmc_pdf': (267, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:pubmed_central': (13, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:pmc_figure': (72, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:pmc_abstract': (99, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:pmc_full-text': (941, 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), u'plosalm:crossref': (15, 'http://dx.doi.org/10.1371/journal.pcbi.1000361')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]



