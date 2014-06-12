from totalimpact import collection, tiredis
from totalimpact import item as item_module
from totalimpact import db, app
from collections import OrderedDict
from totalimpact import REDIS_UNITTEST_DATABASE_NUMBER

import os, json

from nose.tools import raises, assert_equals, assert_true, nottest
import unittest
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests


api_items_loc = os.path.join(
    os.path.split(__file__)[0],
    '../data/items.json')
API_ITEMS_JSON = json.loads(open(api_items_loc, "r").read())


class TestCollection():

    def setUp(self):
        self.d = None

        # do the same thing for the redis db, set up the test redis database.  We're using DB Number 8
        self.r = tiredis.from_url("redis://localhost:6379", db=REDIS_UNITTEST_DATABASE_NUMBER)
        self.r.flushdb()

        self.db = setup_postgres_for_unittests(db, app)

        self.aliases = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]

    def tearDown(self):
        teardown_postgres_for_unittests(self.db)


    def test_init_collection(self):
        #make sure nothing there beforehand
        response = collection.Collection.query.filter_by(cid="socrates").first()
        assert_equals(response, None)

        new_collection = collection.Collection("socrates")
        new_cid = new_collection.cid        
        print new_collection

        # still not there
        response = collection.Collection.query.filter_by(cid="socrates").first()
        assert_equals(response, None)

        self.db.session.add(new_collection)
        self.db.session.commit()

        # and now poof there it is
        response = collection.Collection.query.filter_by(cid="socrates").first()
        assert_equals(response.cid, "socrates")


    def test_collection_with_tiids(self):
        test_tiid = "123213213"
        new_collection_tiid = collection.CollectionTiid(tiid=test_tiid)

        new_collection = collection.Collection("socrates")
        new_cid = new_collection.cid        
        print new_collection

        new_collection.tiid_links = [new_collection_tiid]
        print new_collection.tiids
        assert_equals(new_collection.tiid_links, [new_collection_tiid])

        self.db.session.add(new_collection_tiid)
        self.db.session.add(new_collection)
        self.db.session.commit()

        # and now poof there it is
        response = collection.Collection.query.filter_by(cid="socrates").first()
        assert_equals(response.cid, "socrates")
        assert_equals(response.tiid_links, [new_collection_tiid])
        assert_equals(new_collection_tiid.collection.query.all(), [new_collection])


    def test_create_new_collection(self):
        (coll_doc, collection_object) = collection.create_new_collection(
            cid=None,
            title="mah collection",
            aliases=self.aliases,
            ip_address=None,
            refset_metadata=None,
            myredis=self.r, 
            mydao=self.d)

        assert_equals(coll_doc["title"], "mah collection")
        expected = ['doi:10.124', 'doi:10.125', 'doi:10.123']
        assert_equals(coll_doc["alias_tiids"].keys(), expected)

        assert_equals(collection_object.title, "mah collection")
        expected = [(u'doi', u'10.124'), (u'doi', u'10.125'), (u'doi', u'10.123')]
        assert_equals([added_item.alias_tuple for added_item in collection_object.added_items], expected)
        assert_equals(len(collection_object.tiids), 3)
        found_collection_object = collection.Collection.query.filter_by(cid=collection_object.cid).first()
        assert_equals(found_collection_object.tiids, collection_object.tiids)


    def test_create_new_collection_from_tiids(self):
        tiids = ['234', '345']
        (coll_doc, collection_object) = collection.create_new_collection_from_tiids(
            cid=None,
            title="mah collection",
            tiids=tiids,
            ip_address=None,
            refset_metadata=None)

        assert_equals(coll_doc["title"], "mah collection")
        assert_equals(coll_doc["alias_tiids"].keys(), tiids)

        assert_equals(collection_object.title, "mah collection")
        assert_equals(collection_object.added_items, [])
        assert_equals(collection_object.tiids, tiids)
        found_collection_object = collection.Collection.query.filter_by(cid=collection_object.cid).first()
        assert_equals(found_collection_object.tiids, collection_object.tiids)


    def test_make_creates_identifier(self):
        coll = collection.Collection()
        assert_equals(len(coll.cid), 6)

        coll = collection.Collection(cid="socrates")
        assert_equals(coll.cid, "socrates")


    def test_get_titles(self):
        colls = [
            {"collection_id": "1", "title": "title 1"},
            {"collection_id": "2", "title": "title 2"},
            {"collection_id": "3", "title": "title 3"}
        ]

        for collection_params in colls:
            new_collection = collection.Collection(**collection_params)
            self.db.session.add(new_collection)

        self.db.session.commit()
        titlesDict = collection.get_titles(["1", "2", "3"])
        assert_equals(titlesDict["1"], "title 1")
        assert_equals(titlesDict["3"], "title 3")


    def test_get_metric_value_lists(self):
        response = collection.get_metric_value_lists(API_ITEMS_JSON)
        print response
        assert_equals(response['plosalm:pmc_abstract'], [70, 37, 29, 0])

    def create_test_collection(self):
        test_collection = {"_id": "testcollectionid", 
                            "title": "mycollection", 
                            "type":"collection", 
                            "created":  "2012-08-23T14:40:16.888800", 
                            "last_modified":  "2012-08-23T14:40:16.888800", 
                            "alias_tiids": {
                                       "pmid:16023720": "iaw9rzldigp4xc7p20bycnkg",
                                       "pmid:16413797": "itsq6fgx8ogi9ixysbipmtxx"}}
        test_object = collection.create_objects_from_collection_doc(test_collection) 
        db.session.add(test_object) 

        biblio1 = {
               "journal": "The Astrophysical Journal",
               "authors": "Kwok, Purton, Fitzgerald",
               "year": "1978",
               "title": "On the origin of planetary nebulae"
           }
        biblio2 = {
               "journal": "The Astrophysical Journal 2",
               "authors": "Kwok, Purton, Fitzgerald",
               "year": "1900",
               "title": "On the origin of planetary nebulae The Sequel"
           }
        metrics1 = {
           "mendeley:readers": {
               "provenance_url": "http://www.mendeley.com/research/origin-planetary-nebulae/",
               "values": {
                   "raw_history": {
                       "2013-06-22T20:41:03.178277": 4,
                       "2013-01-15T22:21:55.253826": 3,
                       "2013-07-24T17:59:26.817504": 4,
                       "2013-07-24T18:04:41.035841": 9,
                   },
                   "raw": 9
               }
           },
           "mendeley:discipline": {
               "provenance_url": "http://www.mendeley.com/research/origin-planetary-nebulae/",
               "values": {
                   "raw_history": {
                       "2013-06-22T23:03:15.852461": [
                           {
                               "name": "Astronomy / Astrophysics / Space Science",
                               "value": 100,
                               "id": 2
                           }
                       ]
                    }
                }
            }
        }
        metrics2 = {
           "topsy:tweets": {
               "provenance_url": "http://topsydrilldown",
               "values": {
                   "raw_history": {
                       "2013-11-22T20:41:03.178277": 22
                   },
                   "raw": 22
                }
            }
        }

        test_item_docs = [
            {"_id": "iaw9rzldigp4xc7p20bycnkg", "type":"item", "created": "2012-08-23T14:40:16.888800", "last_modified": "2012-08-23T14:40:16.888800", "biblio":biblio1, "metrics":metrics1, "aliases":{"pmid": ["16023720"]}},
            {"_id": "itsq6fgx8ogi9ixysbipmtxx", "type":"item", "created": "2012-08-23T14:40:16.888800", "last_modified": "2012-08-23T14:40:16.888800", "biblio":biblio2, "metrics":metrics2, "aliases":{"pmid": ["16413797"]}}
        ]

        for item_doc in test_item_docs:
            test_object = item_module.create_objects_from_item_doc(item_doc) 
            db.session.add(test_object) 

        db.session.commit() 


    def test_get_collection_with_items_for_client_no_history(self):
        self.create_test_collection()

        (returned_doc, still_updating) = collection.get_collection_with_items_for_client("testcollectionid", None, self.r, self.d)
        assert_equals(still_updating, False)
        print returned_doc
        print json.dumps(returned_doc, sort_keys=True, indent=4)
        expected =  {'created': '2012-08-23T14:40:16.888800', 'items': [{'created': '2012-08-23T14:40:16.888800', 'currently_updating': False, 'metrics': {u'mendeley:discipline': {'provenance_url': u'http://www.mendeley.com/research/origin-planetary-nebulae/', 'values': {'raw': u'[{"name": "Astronomy / Astrophysics / Space Science", "value": 100, "id": 2}]'}, 'static_meta': {'provider_url': 'http://www.mendeley.com/', 'icon': 'http://www.mendeley.com/favicon.ico', 'display_name': 'discipline, top 3 percentages', 'description': 'Percent of readers by discipline, for top three disciplines (csv, api only)', 'provider': 'Mendeley'}}, u'mendeley:readers': {'provenance_url': u'http://www.mendeley.com/research/origin-planetary-nebulae/', 'values': {'raw': u'9'}, 'static_meta': {'provider_url': 'http://www.mendeley.com/', 'icon': 'http://www.mendeley.com/favicon.ico', 'display_name': 'readers', 'description': 'The number of readers who have added the article to their libraries', 'provider': 'Mendeley'}}}, 'last_modified': '2012-08-23T14:40:16.888800', 'biblio': {'genre': 'article'}, '_id': u'iaw9rzldigp4xc7p20bycnkg', 'type': 'item', 'aliases': {u'pmid': [u'16023720']}}, {'created': '2012-08-23T14:40:16.888800', 'currently_updating': False, 'metrics': {u'topsy:tweets': {'provenance_url': u'http://topsydrilldown', 'values': {'raw': u'22'}, 'static_meta': {'provider_url': 'http://www.topsy.com/', 'icon': 'http://twitter.com/phoenix/favicon.ico', 'display_name': 'tweets', 'description': 'Number of times the item has been tweeted', 'provider': 'Topsy'}}}, 'last_modified': '2012-08-23T14:40:16.888800', 'biblio': {'genre': 'article'}, '_id': u'itsq6fgx8ogi9ixysbipmtxx', 'type': 'item', 'aliases': {u'pmid': [u'16413797']}}], 'title': u'mycollection', 'alias_tiids': {u'iaw9rzldigp4xc7p20bycnkg': u'iaw9rzldigp4xc7p20bycnkg', u'itsq6fgx8ogi9ixysbipmtxx': u'itsq6fgx8ogi9ixysbipmtxx'}, 'last_modified': '2012-08-23T14:40:16.888800', '_id': u'testcollectionid', 'type': 'collection'}
        print "**"
        print json.dumps(expected, sort_keys=True, indent=4)

        assert_equals(returned_doc, expected)


    def test_get_collection_with_items_for_client_include_history(self):
        self.create_test_collection()

        (returned_doc, still_updating) = collection.get_collection_with_items_for_client("testcollectionid", None, self.r, self.d, include_history=True)
        assert_equals(still_updating, False)
        print returned_doc
        print json.dumps(returned_doc, sort_keys=True, indent=4)
        expected = {'created': '2012-08-23T14:40:16.888800', 'items': [{'created': '2012-08-23T14:40:16.888800', 'currently_updating': False, 'metrics': {u'mendeley:discipline': {'provenance_url': u'http://www.mendeley.com/research/origin-planetary-nebulae/', 'values': {'raw': u'[{"name": "Astronomy / Astrophysics / Space Science", "value": 100, "id": 2}]', 'raw_history': {'2013-06-22T23:03:15.852461': u'[{"name": "Astronomy / Astrophysics / Space Science", "value": 100, "id": 2}]'}}, 'static_meta': {'provider_url': 'http://www.mendeley.com/', 'icon': 'http://www.mendeley.com/favicon.ico', 'display_name': 'discipline, top 3 percentages', 'description': 'Percent of readers by discipline, for top three disciplines (csv, api only)', 'provider': 'Mendeley'}}, u'mendeley:readers': {'provenance_url': u'http://www.mendeley.com/research/origin-planetary-nebulae/', 'values': {'raw': u'9', 'raw_history': {'2013-07-24T18:04:41.035841': u'9'}}, 'static_meta': {'provider_url': 'http://www.mendeley.com/', 'icon': 'http://www.mendeley.com/favicon.ico', 'display_name': 'readers', 'description': 'The number of readers who have added the article to their libraries', 'provider': 'Mendeley'}}}, 'last_modified': '2012-08-23T14:40:16.888800', 'biblio': {'genre': 'article'}, '_id': u'iaw9rzldigp4xc7p20bycnkg', 'type': 'item', 'aliases': {u'pmid': [u'16023720']}}, {'created': '2012-08-23T14:40:16.888800', 'currently_updating': False, 'metrics': {u'topsy:tweets': {'provenance_url': u'http://topsydrilldown', 'values': {'raw': u'22', 'raw_history': {'2013-11-22T20:41:03.178277': u'22'}}, 'static_meta': {'provider_url': 'http://www.topsy.com/', 'icon': 'http://twitter.com/phoenix/favicon.ico', 'display_name': 'tweets', 'description': 'Number of times the item has been tweeted', 'provider': 'Topsy'}}}, 'last_modified': '2012-08-23T14:40:16.888800', 'biblio': {'genre': 'article'}, '_id': u'itsq6fgx8ogi9ixysbipmtxx', 'type': 'item', 'aliases': {u'pmid': [u'16413797']}}], 'title': u'mycollection', 'alias_tiids': {u'iaw9rzldigp4xc7p20bycnkg': u'iaw9rzldigp4xc7p20bycnkg', u'itsq6fgx8ogi9ixysbipmtxx': u'itsq6fgx8ogi9ixysbipmtxx'}, 'last_modified': '2012-08-23T14:40:16.888800', '_id': u'testcollectionid', 'type': 'collection'}
        #print json.dumps(expected, sort_keys=True, indent=4)

        assert_equals(returned_doc, expected)


    def test_add_items_to_collection(self):
        self.create_test_collection()
        cid = "testcollectionid"

        # try a doi
        assert_equals(len(collection.Collection.query.get(cid).tiids), 2)
        collection_object = collection.add_items_to_collection(
            cid=cid, 
            aliases=[("doi", "10.1371/journal.pone.0004803")], 
            myredis=self.r)
        assert_equals(len(collection_object.tiids), 3)
        assert_equals(len(collection.Collection.query.get(cid).tiids), 3)

        test_biblio = {
                "authors": "Milojevi\u0107, Hemminger, Priem, Chen, Leydesdorff, Weingart",
                "first_author": "Milojevi\u0107",
                "first_page": "1",
                "genre": "unknown",
                "journal": "Proceedings of the American Society for Information Science and Technology",
                "number": "1",
                "title": "Information visualization state of the art and future directions",
                "volume": "49",
                "year": "2012"
            }

        # try a biblio
        collection_object = collection.add_items_to_collection(
            cid=cid, 
            aliases=[("biblio", test_biblio)],
            myredis=self.r)
        assert_equals(len(collection_object.tiids), 4)
        assert_equals(len(collection.Collection.query.get(cid).tiids), 4)

        # try the biblio again... now it adds a new one
        collection_object = collection.add_items_to_collection(
            cid=cid, 
            aliases=[("biblio", test_biblio)],
            myredis=self.r)

        assert_equals(len(collection_object.tiids), 5)
        assert_equals(len(collection.Collection.query.get(cid).tiids), 5)



    def test_make_csv_rows(self):
        csv = collection.make_csv_rows(API_ITEMS_JSON)
        expected = (OrderedDict([('tiid', u'f2dc3f36b1da11e19199c8bcc8937e3f'), ('title', 'Design Principles for Riboswitch Function'), ('doi', '10.1371/journal.pcbi.1000363'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 4), (u'mendeley:readers', 57), (u'plosalm:crossref', 16), (u'plosalm:html_views', 3361), (u'plosalm:pdf_views', 1112), (u'plosalm:pmc_abstract', 37), (u'plosalm:pmc_figure', 54), (u'plosalm:pmc_full-text', 434), (u'plosalm:pmc_pdf', 285), (u'plosalm:pmc_supp-data', 41), (u'plosalm:pmc_unique-ip', 495), (u'plosalm:pubmed_central', 9), (u'plosalm:scopus', 19), (u'wikipedia:mentions', '')]), [OrderedDict([('tiid', u'f2b45fcab1da11e19199c8bcc8937e3f'), ('title', 'Tumor-Immune Interaction, Surgical Treatment, and Cancer Recurrence in a Mathematical Model of Melanoma'), ('doi', '10.1371/journal.pcbi.1000362'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 1), (u'mendeley:readers', 13), (u'plosalm:crossref', 7), (u'plosalm:html_views', 2075), (u'plosalm:pdf_views', 484), (u'plosalm:pmc_abstract', 29), (u'plosalm:pmc_figure', 13), (u'plosalm:pmc_full-text', 232), (u'plosalm:pmc_pdf', 113), (u'plosalm:pmc_supp-data', 0), (u'plosalm:pmc_unique-ip', 251), (u'plosalm:pubmed_central', 2), (u'plosalm:scopus', 11), (u'wikipedia:mentions', '')]), OrderedDict([('tiid', u'c1eba010b1da11e19199c8bcc8937e3f'), ('title', 'Data from: Comparison of quantitative and molecular genetic variation of native vs. invasive populations of purple loosestrife (Lythrum salicaria L., Lythraceae)'), ('doi', '10.5061/dryad.1295'), (u'dryad:most_downloaded_file', 70), (u'dryad:package_views', 537), (u'dryad:total_downloads', 114), (u'mendeley:groups', ''), (u'mendeley:readers', ''), (u'plosalm:crossref', ''), (u'plosalm:html_views', ''), (u'plosalm:pdf_views', ''), (u'plosalm:pmc_abstract', ''), (u'plosalm:pmc_figure', ''), (u'plosalm:pmc_full-text', ''), (u'plosalm:pmc_pdf', ''), (u'plosalm:pmc_supp-data', ''), (u'plosalm:pmc_unique-ip', ''), (u'plosalm:pubmed_central', ''), (u'plosalm:scopus', ''), (u'wikipedia:mentions', '')]), OrderedDict([('tiid', u'c202754cb1da11e19199c8bcc8937e3f'), ('title', 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article'), ('doi', '10.1371/journal.pcbi.1000361'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 4), (u'mendeley:readers', 52), (u'plosalm:crossref', 13), (u'plosalm:html_views', 11521), (u'plosalm:pdf_views', 1097), (u'plosalm:pmc_abstract', 70), (u'plosalm:pmc_figure', 39), (u'plosalm:pmc_full-text', 624), (u'plosalm:pmc_pdf', 149), (u'plosalm:pmc_supp-data', 6), (u'plosalm:pmc_unique-ip', 580), (u'plosalm:pubmed_central', 12), (u'plosalm:scopus', 19), (u'wikipedia:mentions', 1)]), OrderedDict([('tiid', u'f2dc3f36b1da11e19199c8bcc8937e3f'), ('title', 'Design Principles for Riboswitch Function'), ('doi', '10.1371/journal.pcbi.1000363'), (u'dryad:most_downloaded_file', ''), (u'dryad:package_views', ''), (u'dryad:total_downloads', ''), (u'mendeley:groups', 4), (u'mendeley:readers', 57), (u'plosalm:crossref', 16), (u'plosalm:html_views', 3361), (u'plosalm:pdf_views', 1112), (u'plosalm:pmc_abstract', 37), (u'plosalm:pmc_figure', 54), (u'plosalm:pmc_full-text', 434), (u'plosalm:pmc_pdf', 285), (u'plosalm:pmc_supp-data', 41), (u'plosalm:pmc_unique-ip', 495), (u'plosalm:pubmed_central', 9), (u'plosalm:scopus', 19), (u'wikipedia:mentions', '')])])
        assert_equals(csv, expected)

    def test_make_csv_stream(self):
        csv = collection.make_csv_stream(API_ITEMS_JSON)
        expected = 'tiid,title,doi,dryad:most_downloaded_file,dryad:package_views,dryad:total_downloads,mendeley:groups,mendeley:readers,plosalm:crossref,plosalm:html_views,plosalm:pdf_views,plosalm:pmc_abstract,plosalm:pmc_figure,plosalm:pmc_full-text,plosalm:pmc_pdf,plosalm:pmc_supp-data,plosalm:pmc_unique-ip,plosalm:pubmed_central,plosalm:scopus,wikipedia:mentions\r\nf2b45fcab1da11e19199c8bcc8937e3f,"Tumor-Immune Interaction, Surgical Treatment, and Cancer Recurrence in a Mathematical Model of Melanoma",10.1371/journal.pcbi.1000362,,,,1,13,7,2075,484,29,13,232,113,0,251,2,11,\r\nc1eba010b1da11e19199c8bcc8937e3f,"Data from: Comparison of quantitative and molecular genetic variation of native vs. invasive populations of purple loosestrife (Lythrum salicaria L., Lythraceae)",10.5061/dryad.1295,70,537,114,,,,,,,,,,,,,,\r\nc202754cb1da11e19199c8bcc8937e3f,Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article,10.1371/journal.pcbi.1000361,,,,4,52,13,11521,1097,70,39,624,149,6,580,12,19,1\r\nf2dc3f36b1da11e19199c8bcc8937e3f,Design Principles for Riboswitch Function,10.1371/journal.pcbi.1000363,,,,4,57,16,3361,1112,37,54,434,285,41,495,9,19,\r\n'
        assert_equals(csv, expected)

    def test_get_metric_values_of_reference_sets(self):
        response = collection.get_metric_values_of_reference_sets(API_ITEMS_JSON)
        print response
        assert_equals(response['mendeley:readers'], [57, 52, 13, 0])

    def test_get_normalization_confidence_interval_ranges(self):
        input = {"facebook:shares": [1, 0, 0, 0],
            "mendeley:readers": [10, 9, 8, 7],
            'mendeley:groups': [0, 0, 0, 0]
            }
        table = [(0, 30), (10, 60), (40, 80), (50, 90), (60, 97)]
        response = collection.get_normalization_confidence_interval_ranges(input, table)
        print response
        expected = {'facebook:shares': {0: {'CI95_lower': 0,
                                           'CI95_upper': 80,
                                           'estimate_lower': 0,
                                           'estimate_upper': 50},
                                          1: {'CI95_lower': 50,
                                           'CI95_upper': 90,
                                           'estimate_lower': 75,
                                           'estimate_upper': 75},
                                          2: {'CI95_lower': 61,
                                           'CI95_upper': 100,
                                           'estimate_lower': 100,
                                           'estimate_upper': 100}},
                      'mendeley:groups': {0: {'CI95_lower': 0,
                                           'CI95_upper': 90,
                                           'estimate_lower': 0,
                                           'estimate_upper': 75},
                                          1: {'CI95_lower': 61,
                                           'CI95_upper': 100,
                                           'estimate_lower': 100,
                                           'estimate_upper': 100}},
                      'mendeley:readers': {7: {'CI95_lower': 0,
                                           'CI95_upper': 30,
                                           'estimate_lower': 0,
                                           'estimate_upper': 0},
                                          8: {'CI95_lower': 10,
                                           'CI95_upper': 60,
                                           'estimate_lower': 25,
                                           'estimate_upper': 25},
                                          9: {'CI95_lower': 40,
                                           'CI95_upper': 80,
                                           'estimate_lower': 50,
                                           'estimate_upper': 50},
                                          10: {'CI95_lower': 50,
                                           'CI95_upper': 90,
                                           'estimate_lower': 75,
                                           'estimate_upper': 75},
                                          11: {'CI95_lower': 61,
                                           'CI95_upper': 100,
                                           'estimate_lower': 100,
                                           'estimate_upper': 100}}}

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
