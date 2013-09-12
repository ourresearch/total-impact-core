import os, collections, simplejson

from totalimpact import db, app
from totalimpact.providers import pmc
from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderFactory
from totalimpact import provider_batch_data
from test.utils import http
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

from nose.tools import assert_equals, raises, nottest, assert_items_equal

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/pmc")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "monthly_download")
SAMPLE_EXTRACT_METRICS_PAGE_DIFFERENT_MONTH = os.path.join(datadir, "monthly_download_different_month")

TEST_PMID = "23066504"

class TestPmc(ProviderTestCase):

    provider_name = "pmc"

    testitem_aliases = ("pmid", TEST_PMID)
    testitem_metrics = ("pmid", TEST_PMID)

    def setUp(self):
        ProviderTestCase.setUp(self)

        self.db = setup_postgres_for_unittests(db, app)

        sample_data_dump = open(SAMPLE_EXTRACT_METRICS_PAGE, "r").read()
        sample_data_dump_different_month = open(SAMPLE_EXTRACT_METRICS_PAGE_DIFFERENT_MONTH, "r").read()

        test_monthly_data = [
            {"_id": "abc", 
                "type": "provider_data_dump", 
                "provider": "pmc", 
                "raw": sample_data_dump,
                "provider_raw_version": 1.0,
                "created": "2012-11-29T07:34:01.126892",
                "aliases": {"pmid":["111", "222"]},
                "min_event_date": "2012-10-01T07:34:01.126892",
                "max_event_date": "2012-10-31T07:34:01.126892"
            },
            {"_id": "def", 
                "type": "provider_data_dump", 
                "provider": "pmc", 
                "raw": sample_data_dump_different_month,
                "provider_raw_version": 1.0,
                "created": "2012-11-29T08:34:01.126892",
                "aliases": {"pmid":["111"]},
                "min_event_date": "2012-01-01T07:34:01.126892",
                "max_event_date": "2012-01-31T07:34:01.126892"
            },
            {
               "_id": "abc123",
               "raw": "<pmc-web-stat><request year=\"2012\" month=\"10\" jrid=\"elife\" eissn=\"2050-084X\"></request><response status=\"0\" collection=\"eLife\"></response><articles><article id=\"PMC3463246\"><meta-data doi=\"10.7554/eLife.00013\" pmcid=\"PMC3463246\" pubmed-id=\"23066504\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00013\"/><usage unique-ip=\"1368\" full-text=\"1464\" pdf=\"722\" abstract=\"119\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"144\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3463247\"><meta-data doi=\"10.7554/eLife.00240\" pmcid=\"PMC3463247\" pubmed-id=\"23066507\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00240\"/><usage unique-ip=\"514\" full-text=\"606\" pdf=\"230\" abstract=\"0\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"9\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3465569\"><meta-data doi=\"10.7554/eLife.00242\" pmcid=\"PMC3465569\" pubmed-id=\"23066508\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00242\"/><usage unique-ip=\"473\" full-text=\"503\" pdf=\"181\" abstract=\"2\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"13\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3465570\"><meta-data doi=\"10.7554/eLife.00243\" pmcid=\"PMC3465570\" pubmed-id=\"23066509\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00243\"/><usage unique-ip=\"547\" full-text=\"636\" pdf=\"227\" abstract=\"1\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"56\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3466591\"><meta-data doi=\"10.7554/eLife.00065\" pmcid=\"PMC3466591\" pubmed-id=\"23066506\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00065\"/><usage unique-ip=\"2516\" full-text=\"2804\" pdf=\"1583\" abstract=\"195\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"405\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3466783\"><meta-data doi=\"10.7554/eLife.00007\" pmcid=\"PMC3466783\" pubmed-id=\"23066503\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00007\"/><usage unique-ip=\"1331\" full-text=\"1412\" pdf=\"898\" abstract=\"224\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"109\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3467772\"><meta-data doi=\"10.7554/eLife.00270\" pmcid=\"PMC3467772\" pubmed-id=\"23066510\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00270\"/><usage unique-ip=\"1396\" full-text=\"1776\" pdf=\"625\" abstract=\"4\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"0\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3470722\"><meta-data doi=\"10.7554/eLife.00286\" pmcid=\"PMC3470722\" pubmed-id=\"23071903\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00286\"/><usage unique-ip=\"909\" full-text=\"1030\" pdf=\"376\" abstract=\"6\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"0\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3479833\"><meta-data doi=\"10.7554/eLife.00031\" pmcid=\"PMC3479833\" pubmed-id=\"23110253\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00031\"/><usage unique-ip=\"154\" full-text=\"126\" pdf=\"87\" abstract=\"26\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"13\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3470409\"><meta-data doi=\"10.7554/eLife.00048\" pmcid=\"PMC3470409\" pubmed-id=\"23066505\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00048\"/><usage unique-ip=\"1250\" full-text=\"1361\" pdf=\"911\" abstract=\"237\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"317\" supp-data=\"4\" cited-by=\"0\"/></article><article id=\"PMC3482692\"><meta-data doi=\"10.7554/eLife.00102\" pmcid=\"PMC3482692\" pubmed-id=\"23110254\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00102\"/><usage unique-ip=\"259\" full-text=\"232\" pdf=\"133\" abstract=\"36\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"8\" supp-data=\"3\" cited-by=\"0\"/></article><article id=\"PMC3482687\"><meta-data doi=\"10.7554/eLife.00281\" pmcid=\"PMC3482687\" pubmed-id=\"23110255\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00281\"/><usage unique-ip=\"75\" full-text=\"53\" pdf=\"47\" abstract=\"0\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"1\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3482686\"><meta-data doi=\"10.7554/eLife.00005\" pmcid=\"PMC3482686\" pubmed-id=\"23110252\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00005\"/><usage unique-ip=\"324\" full-text=\"249\" pdf=\"263\" abstract=\"71\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"93\" supp-data=\"17\" cited-by=\"0\"/></article></articles></pmc-web-stat>",
               "max_event_date": "2012-10-31T07:34:01.126892",
               "provider": "pmc",
               "aliases": {
                   "pmid": [
                       "23066504",
                       "23066507",
                       "23066508",
                       "23066509",
                       "23066506",
                       "23066503",
                       "23066510",
                       "23071903",
                       "23110253",
                       "23066505",
                       "23110254",
                       "23110255",
                       "23110252"
                   ]
               },
               "provider_raw_version": 1,
               "type": "provider_data_dump",
               "min_event_date": "2012-10-02T07:34:01.126892",
               "created": "2012-11-29T09:34:01.126892"
            }
        ]
        #print test_monthly_data
        for doc in test_monthly_data:
            new_object = provider_batch_data.create_objects_from_doc(doc)
            print new_object

        self.provider = pmc.Pmc()
        print "after pmc"

    def tearDown(self):
        teardown_postgres_for_unittests(self.db)


    def test_has_applicable_batch_data_true(self):
        # ensure that it matches an appropriate ids
        response = self.provider.has_applicable_batch_data("pmid", "111")
        assert_equals(response, True)

    def test_has_applicable_batch_data_false(self):
        # ensure that it matches an appropriate ids
        response = self.provider.has_applicable_batch_data("pmid", "notapmidintheview")
        assert_equals(response, False)

    def test_build_batch_data_dict(self):
        # ensure that it matches an appropriate ids
        response = self.provider.build_batch_data_dict()
        #print response
        print response.keys()
        expected = [('pmid', '23071903'), ('pmid', '23066503'), ('pmid', '111'), ('pmid', '23110254'), ('pmid', '23110252'), ('pmid', '23066505'), ('pmid', '23066504'), ('pmid', '23110255'), ('pmid', '23066507'), ('pmid', '23066506'), ('pmid', '23066510'), ('pmid', '23066509'), ('pmid', '23066508'), ('pmid', '222'), ('pmid', '23110253')]
        assert_items_equal(response.keys(), expected)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        good_page = f.read()
        metrics_dict = self.provider._extract_metrics(good_page, id="222")
        print metrics_dict
        expected = {'pmc:unique_ip_views': 514, 'pmc:pdf_downloads': 230, 'pmc:fulltext_views': 606, 'pmc:figure_views': 9}
        assert_equals(metrics_dict, expected)

    def test_provider_metrics_500(self):
        pass  # Not applicable

    def test_provider_metrics_400(self):
        pass  # Not applicable

    def test_provider_metrics_nonsense_xml(self):
        pass  # Not applicable

    def test_provider_metrics_nonsense_txt(self):
        pass  # Not applicable

    def test_provider_metrics_empty(self):
        pass  # Not applicable

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([("pmid", "222")])
        expected = {'pmc:unique_ip_views': (514, ''), 'pmc:pdf_downloads': (230, ''), 'pmc:fulltext_views': (606, ''), 'pmc:figure_views': (9, '')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_multiple_months(self):
        metrics_dict = self.provider.metrics([("pmid", "111")])
        expected = {'pmc:abstract_views': (218, ''), 'pmc:pdf_downloads': (810, ''), 'pmc:fulltext_views': (1530, ''), 'pmc:figure_views': (177, ''), 'pmc:unique_ip_views': (1923, '')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_real(self):
        metrics_dict = self.provider.metrics([("pmid", "23066504")])
        expected = {'pmc:abstract_views': (119, ''), 'pmc:pdf_downloads': (722, ''), 'pmc:fulltext_views': (1464, ''), 'pmc:figure_views': (144, ''), 'pmc:unique_ip_views': (1368, '')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

