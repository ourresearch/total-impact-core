from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.api import app

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
        expected = {u'plosalm:pmc_supp-data': 157, 'plosalm:html_views': 17455, u'plosalm:pmc_abstract': 19, u'plosalm:pmc_unique-ip': 963, u'plosalm:scopus': 218, 'plosalm:pdf_views': 2106, u'plosalm:pmc_pdf': 419, u'plosalm:pmc_full-text': 1092, u'plosalm:pmc_figure': 71, u'plosalm:pubmed_central': 102, u'plosalm:crossref': 133}

        assert_equals(metrics_dict, expected)


