from totalimpact import collection
from collections import OrderedDict
import os, json

from nose.tools import raises, assert_equals, nottest
import unittest

api_items_loc = os.path.join(
    os.path.split(__file__)[0],
    '../data/items.json')
API_ITEMS_JSON = json.loads(open(api_items_loc, "r").read())


class TestCollection():

    def test_make_creates_identifier(self):
        coll, key = collection.make()
        assert_equals(len(coll["_id"]), 6)

    def test_make_sets_owner(self):
        coll, key = collection.make()
        assert_equals(coll["owner"], None)

        coll, key = collection.make("socrates")
        assert_equals(coll["owner"], "socrates")

    def test_create_returns_collection_and_update_key(self):
        coll, key = collection.make()
        assert collection.check_password_hash(coll["key_hash"], key)

    def test_claim_collection(self):
        coll, key = collection.make("socrates")
        assert_equals(coll["owner"], "socrates")

        coll = collection.claim_collection(coll, "plato", key)
        assert_equals(coll["owner"], "plato")

    @raises(ValueError)
    def test_claim_collection_fails_with_wrong_key(self):
        coll, key = collection.make("socrates")
        assert_equals(coll["owner"], "socrates")

        coll = collection.claim_collection(coll, "plato", "wrong key")
        assert_equals(coll["owner"], "plato")

    @raises(ValueError)
    def test_claim_collection_fails_if_key_hash_not_set(self):
        coll, key = collection.make("socrates")
        assert_equals(coll["owner"], "socrates")
        del coll["key_hash"]

        coll = collection.claim_collection(coll, "plato", key)
        assert_equals(coll["owner"], "plato")

    def test_get_metric_value_lists(self):
        response = collection.get_metric_value_lists(API_ITEMS_JSON)
        expected = {u'plosalm:pmc_abstract': [70, 37, 29, 0], u'dryad:package_views': [537, 0, 0, 0], u'plosalm:pmc_unique-ip': [580, 495, 251, 0], u'wikipedia:mentions': [1, 0, 0, 0], u'plosalm:html_views': [11521, 3361, 2075, 0], u'plosalm:pmc_supp-data': [41, 6, 0, 0], u'plosalm:pdf_views': [1112, 1097, 484, 0], u'plosalm:scopus': [19, 19, 11, 0], u'dryad:most_downloaded_file': [70, 0, 0, 0], u'plosalm:pmc_pdf': [285, 149, 113, 0], u'plosalm:pubmed_central': [12, 9, 2, 0], u'plosalm:pmc_figure': [54, 39, 13, 0], u'mendeley:readers': [57, 52, 13, 0], u'dryad:total_downloads': [114, 0, 0, 0], u'plosalm:pmc_full-text': [624, 434, 232, 0], u'mendeley:groups': [4, 4, 1, 0], u'plosalm:crossref': [16, 13, 7, 0]}
        assert_equals(response, expected)

    def test_make_csv_rows(self):
        csv = collection.make_csv_rows(API_ITEMS_JSON)
        expected = (OrderedDict([('tiid', u'f2dc3f36b1da11e19199c8bcc8937e3f'), ('title', 'Design Principles for Riboswitch Function'), ('doi', '10.1371/journal.pcbi.1000363'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 4), (u'mendeley:readers', 57), (u'plosalm:crossref', 16), (u'plosalm:html_views', 3361), (u'plosalm:pdf_views', 1112), (u'plosalm:pmc_abstract', 37), (u'plosalm:pmc_figure', 54), (u'plosalm:pmc_full-text', 434), (u'plosalm:pmc_pdf', 285), (u'plosalm:pmc_supp-data', 41), (u'plosalm:pmc_unique-ip', 495), (u'plosalm:pubmed_central', 9), (u'plosalm:scopus', 19), (u'wikipedia:mentions', '')]), [OrderedDict([('tiid', u'f2b45fcab1da11e19199c8bcc8937e3f'), ('title', 'Tumor-Immune Interaction, Surgical Treatment, and Cancer Recurrence in a Mathematical Model of Melanoma'), ('doi', '10.1371/journal.pcbi.1000362'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 1), (u'mendeley:readers', 13), (u'plosalm:crossref', 7), (u'plosalm:html_views', 2075), (u'plosalm:pdf_views', 484), (u'plosalm:pmc_abstract', 29), (u'plosalm:pmc_figure', 13), (u'plosalm:pmc_full-text', 232), (u'plosalm:pmc_pdf', 113), (u'plosalm:pmc_supp-data', 0), (u'plosalm:pmc_unique-ip', 251), (u'plosalm:pubmed_central', 2), (u'plosalm:scopus', 11), (u'wikipedia:mentions', '')]), OrderedDict([('tiid', u'c1eba010b1da11e19199c8bcc8937e3f'), ('title', 'data from: comparison of quantitative and molecular genetic variation of native vs. invasive populations of purple loosestrife (lythrum salicaria l., lythraceae)'), ('doi', '10.5061/dryad.1295'), (u'dryad:most_downloaded_file', 70), (u'dryad:package_views', 537), (u'dryad:total_downloads', 114), (u'mendeley:groups', ''), (u'mendeley:readers', ''), (u'plosalm:crossref', ''), (u'plosalm:html_views', ''), (u'plosalm:pdf_views', ''), (u'plosalm:pmc_abstract', ''), (u'plosalm:pmc_figure', ''), (u'plosalm:pmc_full-text', ''), (u'plosalm:pmc_pdf', ''), (u'plosalm:pmc_supp-data', ''), (u'plosalm:pmc_unique-ip', ''), (u'plosalm:pubmed_central', ''), (u'plosalm:scopus', ''), (u'wikipedia:mentions', '')]), OrderedDict([('tiid', u'c202754cb1da11e19199c8bcc8937e3f'), ('title', 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article'), ('doi', '10.1371/journal.pcbi.1000361'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 4), (u'mendeley:readers', 52), (u'plosalm:crossref', 13), (u'plosalm:html_views', 11521), (u'plosalm:pdf_views', 1097), (u'plosalm:pmc_abstract', 70), (u'plosalm:pmc_figure', 39), (u'plosalm:pmc_full-text', 624), (u'plosalm:pmc_pdf', 149), (u'plosalm:pmc_supp-data', 6), (u'plosalm:pmc_unique-ip', 580), (u'plosalm:pubmed_central', 12), (u'plosalm:scopus', 19), (u'wikipedia:mentions', 1)]), OrderedDict([('tiid', u'f2dc3f36b1da11e19199c8bcc8937e3f'), ('title', 'Design Principles for Riboswitch Function'), ('doi', '10.1371/journal.pcbi.1000363'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 4), (u'mendeley:readers', 57), (u'plosalm:crossref', 16), (u'plosalm:html_views', 3361), (u'plosalm:pdf_views', 1112), (u'plosalm:pmc_abstract', 37), (u'plosalm:pmc_figure', 54), (u'plosalm:pmc_full-text', 434), (u'plosalm:pmc_pdf', 285), (u'plosalm:pmc_supp-data', 41), (u'plosalm:pmc_unique-ip', 495), (u'plosalm:pubmed_central', 9), (u'plosalm:scopus', 19), (u'wikipedia:mentions', '')])])
        assert_equals(csv, expected)

    def test_make_csv_stream(self):
        csv = collection.make_csv_stream(API_ITEMS_JSON)
        expected = 'tiid,title,doi,dryad:most_downloaded_file,dryad:package_views,dryad:total_downloads,mendeley:groups,mendeley:readers,plosalm:crossref,plosalm:html_views,plosalm:pdf_views,plosalm:pmc_abstract,plosalm:pmc_figure,plosalm:pmc_full-text,plosalm:pmc_pdf,plosalm:pmc_supp-data,plosalm:pmc_unique-ip,plosalm:pubmed_central,plosalm:scopus,wikipedia:mentions\r\nf2b45fcab1da11e19199c8bcc8937e3f,"Tumor-Immune Interaction, Surgical Treatment, and Cancer Recurrence in a Mathematical Model of Melanoma",10.1371/journal.pcbi.1000362,,,,1,13,7,2075,484,29,13,232,113,0,251,2,11,\r\nc1eba010b1da11e19199c8bcc8937e3f,"data from: comparison of quantitative and molecular genetic variation of native vs. invasive populations of purple loosestrife (lythrum salicaria l., lythraceae)",10.5061/dryad.1295,70,537,114,,,,,,,,,,,,,,\r\nc202754cb1da11e19199c8bcc8937e3f,Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article,10.1371/journal.pcbi.1000361,,,,4,52,13,11521,1097,70,39,624,149,6,580,12,19,1\r\nf2dc3f36b1da11e19199c8bcc8937e3f,Design Principles for Riboswitch Function,10.1371/journal.pcbi.1000363,,,,4,57,16,3361,1112,37,54,434,285,41,495,9,19,\r\n'
        assert_equals(csv, expected)

    def test_get_normalization_numbers(self):
        response = collection.get_normalization_numbers(API_ITEMS_JSON)
        expected = {u'dryad:package_views': [537, 0, 0, 0], u'wikipedia:mentions': [1, 0, 0, 0], u'dryad:most_downloaded_file': [70, 0, 0, 0], u'mendeley:readers': [57, 52, 13, 0], u'dryad:total_downloads': [114, 0, 0, 0], u'mendeley:groups': [4, 4, 1, 0]}
        assert_equals(response, expected)

    def test_get_normalization_confidence_interval_ranges(self):
        input = {"facebook:shares": [1, 0, 0, 0],
            "mendeley:readers": [10, 9, 8, 7]}
        response = collection.get_normalization_confidence_interval_ranges(input)
        print response
        expected = {'facebook:shares': {0: (2, 79), 1: (76, 98)}, 'mendeley:readers': {8: (20, 24), 9: (76, 79), 10: (76, 98), 7: (2, 24)}}
        assert_equals(response, expected)

        input = {"mendeley:readers": [10, 9, 9, 5, 5, 5, 4, 4, 4, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], "mendeley:groups": [3, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}
        response = collection.get_normalization_confidence_interval_ranges(input)
        print response
        expected = {'mendeley:groups': {0: (1, 94), 1: (79, 98), 2: (87, 99), 3: (91, 99)}, 'mendeley:readers': {0: (1, 60), 1: (36, 66), 2: (42, 82), 3: (61, 88), 4: (71, 93), 5: (77, 97), 9: (85, 99), 10: (91, 99)}}
        assert_equals(response, expected)

    def test_calc_table_internals(self):
        # from http://www.milefoot.com/math/stat/ci-medians.htm
        response = collection.calc_confidence_interval_table(9, 0.80, [50])
        assert_equals(response["range_sum"][50], 0.8203125)
        assert_equals(response["limits"][50], (3,7))

        # from https://onlinecourses.science.psu.edu/stat414/book/export/html/231
        response = collection.calc_confidence_interval_table(9, 0.90, [50])
        assert_equals(response["range_sum"][50], 0.9609375)
        assert_equals(response["limits"][50], (2,8))

        # from https://onlinecourses.science.psu.edu/stat414/book/export/html/231
        response = collection.calc_confidence_interval_table(14, 0.90, [50])
        assert_equals(response["range_sum"][50], 0.942626953125)
        assert_equals(response["limits"][50], (4,11))

    def test_calc_table_extremes(self):
        response = collection.calc_confidence_interval_table(9, 0.95, [90])
        assert_equals(response["range_sum"][90], 0.9916689060000001)
        assert_equals(response["limits"][90], (6,10))

        response = collection.calc_confidence_interval_table(9, 0.95, [10])
        assert_equals(response["range_sum"][10], 0.9916689060000002)
        assert_equals(response["limits"][10], (0,4))

    def test_calc_table(self):
        response = collection.calc_confidence_interval_table(9, 0.95, [i*10 for i in range(10)])
        print response["lookup_table"]
        expected = [(10, 30), (10, 40), (10, 60), (20, 60), (30, 70), (40, 80), (50, 90), (60, 90), (70, 90)]
        assert_equals(response["lookup_table"], expected)

        response = collection.calc_confidence_interval_table(50, 0.95, range(100))
        print response["lookup_table"]
        expected = [(1, 9), (1, 13), (2, 15), (3, 17), (5, 21), (6, 23), (7, 25), (8, 27), (10, 29), (12, 33), (13, 35), (14, 37), (16, 39), (18, 41), (20, 43), (21, 45), (22, 47), (24, 49), (26, 50), (28, 52), (30, 54), (32, 56), (33, 58), (34, 60), (36, 62), (38, 64), (40, 66), (42, 67), (44, 68), (46, 70), (48, 72), (50, 74), (51, 76), (53, 78), (55, 79), (57, 80), (59, 82), (61, 84), (63, 86), (65, 87), (67, 88), (71, 90), (73, 92), (75, 93), (77, 94), (79, 95), (83, 97), (85, 98), (87, 99), (91, 99)]
        assert_equals(response["lookup_table"], expected)
