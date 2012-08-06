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
        assert_equals(response, "http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361")

        response = self.provider.provenance_url("plosalm:scopus", [self.testitem_aliases])
        assert_equals(response, "http://www.scopus.com/scopus/inward/citedby.url?doi=10.1371%2Fjournal.pcbi.1000361&rel=R3.0.0&partnerID=OIVxnoIl&md5=5917ea9916ee68b95c2a7968d65927ab")

        response = self.provider.provenance_url("plosalm:pmc_abstract", [self.testitem_aliases])
        assert_equals(response, "http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361")

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page)
        expected = {'plosalm:pmc_supp-data': 15, 'plosalm:html_views': 11856, 'plosalm:pmc_abstract': 96, 'plosalm:pmc_unique-ip': 856, 'plosalm:scopus': 26, 'plosalm:pdf_views': 1134, 'plosalm:pmc_pdf': 257, 'plosalm:pmc_full-text': 896, 'plosalm:pmc_figure': 70, 'plosalm:pubmed_central': 13, 'plosalm:crossref': 14}
        assert_equals(metrics_dict, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {u'plosalm:pmc_supp-data': (15, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), 'plosalm:html_views': (11871, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), u'plosalm:scopus': (26, u'http://www.scopus.com/scopus/inward/citedby.url?doi=10.1371%2Fjournal.pcbi.1000361&rel=R3.0.0&partnerID=OIVxnoIl&md5=5917ea9916ee68b95c2a7968d65927ab'), u'plosalm:pmc_unique-ip': (856, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), 'plosalm:pdf_views': (1137, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), u'plosalm:pmc_pdf': (257, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), u'plosalm:pubmed_central': (13, u'http://www.ncbi.nlm.nih.gov/sites/entrez?db=pubmed&cmd=link&LinkName=pubmed_pmc_refs&from_uid=19381256'), u'plosalm:pmc_figure': (70, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), u'plosalm:pmc_abstract': (96, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), u'plosalm:pmc_full-text': (896, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361'), u'plosalm:crossref': (14, 'http://www.plosreports.org/services/rest?method=usage.stats&doi=10.1371/journal.pcbi.1000361')}
        print metrics_dict
        for key in expected:
            assert(metrics_dict[key] >= expected[key])



