import unittest, json, uuid
from copy import deepcopy
from urllib import quote_plus
import os
from nose.tools import assert_equals, nottest, assert_greater, assert_items_equal

from totalimpact import app, db, views, tiredis, api_user, collection, item as item_module
from totalimpact.providers.dryad import Dryad
from totalimpact import REDIS_UNITTEST_DATABASE_NUMBER

from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests, http


TEST_DRYAD_DOI = "10.5061/dryad.7898"
TEST_PLOS_DOI = "10.1371/journal.pone.0004803"
GOLD_MEMBER_ITEM_CONTENT = ["MEMBERITEM CONTENT"]
TEST_COLLECTION_ID = "TestCollectionId"
TEST_COLLECTION_TIID_LIST = ["tiid1", "tiid2"]
TEST_COLLECTION_TIID_LIST_MODIFIED = ["tiid1", "tiid_different"]

COLLECTION_SEED = json.loads("""{
    "id": "uuid-goes-here",
    "collection_name": "My Collection",
    "owner": "abcdef",
    "created": 1328569452.406,
    "last_modified": 1328569492.406,
    "alias_tiids": {"doi:123": "origtiid1", "github:frank":"origtiid2"}
}""")
COLLECTION_SEED_MODIFIED = deepcopy(COLLECTION_SEED)
COLLECTION_SEED_MODIFIED["alias_tiids"] = dict(zip(["doi:1", "doi:2"], TEST_COLLECTION_TIID_LIST_MODIFIED))

def MOCK_member_items(self, query_string, url=None, cache_enabled=True):
    return(GOLD_MEMBER_ITEM_CONTENT)

# ensures that all the functions in the views.py module will use a local db,
# which we can in turn use for these unit tests.
mydao = None
# do the same for redis, handing it local redis and instruction to use "DB 8" 
# to isolate unit testing
myredis = views.set_redis("redis://localhost:6379", db=8)

class ViewsTester(unittest.TestCase):

    def setUp(self):
        """
        This test item is a lightly-modified version of a real doc from our
        demo collection; it's available at http://total-impact-core.herokuapp.com/collection/kn5auf
        """
        test_item = '''
            {
            "_id": "1aff9dfebea711e1bdf912313d1a5e63",
            "_rev": "968-c7891982fca2ea41346a20b80c2b888d",
            "aliases": {
                "doi": [
                    "10.5061/dryad.j1fd7"
                ],
                "title": [
                    "Data from: Data archiving is a good use of research funds",
                    "data from: data archiving is a good  investment"
                ],
                "url": [
                    "http://datadryad.org/handle/10255/dryad.33537",
                    "http://hdl.handle.net/10255/dryad.33537"
                ]
            },
            "biblio": {
                "authors": "Piwowar, Vision, Whitlock, Piwowar, Vision, Whitlock, Piwowar, Vision, Whitlock",
                "genre": "dataset",
                "h1": "Data from: Data archiving is a good  investment",
                "repository": "Dryad Digital Repository",
                "title": "Data from: Data archiving is a good  investment",
                "year": "2011"
            },
            "created": "2012-06-25T09:21:11.960271",
            "currently_updating": false,
            "last_modified": "2012-11-18T04:57:40.539053",
            "metrics": {
                "delicious:bookmarks": {
                    "provenance_url": "http://www.delicious.com/url/4794ddb7a3e934ba23165af65fcfa9cd",
                    "static_meta": {
                        "description": "The number of bookmarks to this artifact (maximum=100).",
                        "display_name": "bookmarks",
                        "icon": "http://www.delicious.com/favicon.ico",
                        "provider": "Delicious",
                        "provider_url": "http://www.delicious.com/"
                    },
                    "values": {
                        "raw": 1,
                        "raw_history": {
                            "2012-06-23T09:21:16.027149": 1
                        }
                    }
                },
                "dryad:total_downloads": {
                    "provenance_url": "http://dx.doi.org/10.5061/dryad.j1fd7",
                    "static_meta": {
                        "description": "Dryad total downloads: combined number of downloads of the data package and data files",
                        "display_name": "total downloads",
                        "icon": "http:\\/\\/datadryad.org\\/favicon.ico",
                        "provider": "Dryad",
                        "provider_url": "http:\\/\\/www.datadryad.org\\/"
                    },
                    "values": {
                        "dryad": {
                            "CI95_lower": 91,
                            "CI95_upper": 98,
                            "estimate_lower": 96,
                            "estimate_upper": 96
                        },
                        "raw": 207,
                        "raw_history": {
                            "2012-06-25T09:21:16.027149": 132,
                            "2012-06-26T18:05:19.598432": 132,
                            "2012-06-26T20:10:16.858294": 132
                        }
                    }
                }
            },
            "type": "item"
        }
        '''

        self.test_api_user_meta = {    
                    'max_registered_items': 3, 
                    'planned_use': 'individual CV', 
                    'email': "test@example.com", 
                    'notes': '', 
                    'api_key_owner': 'Julia Smith', 
                    "example_url": "", 
                    "organization": "NASA",
                    "prefix": "NASA",
                }

        self.db = setup_postgres_for_unittests(db, app)

        item = item_module.create_objects_from_item_doc(json.loads(test_item))
        self.db.session.add(item)

        self.existing_api_user = api_user.ApiUser(**self.test_api_user_meta)
        self.existing_api_user.api_key = "validkey"  #override randomly assigned key
        self.db.session.add(self.existing_api_user)
        self.db.session.commit()


        # do the same thing for the redis db.  We're using DB 8 for unittests.
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()

        #setup api test client
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

        # Mock out relevant methods of the Dryad provider
        self.orig_Dryad_member_items = Dryad.member_items
        Dryad.member_items = MOCK_member_items

        self.aliases = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]


    def tearDown(self):
        teardown_postgres_for_unittests(self.db)
        Dryad.member_items = self.orig_Dryad_member_items


    def test_does_not_require_key_if_preversioned_url(self):
        resp = self.client.get("/")
        assert_equals(resp.status_code, 200)

    def test_forbidden_if_no_key_in_v1(self):
        resp = self.client.get("/v1/provider")
        assert_equals(resp.status_code, 403)

    def test_ok_if_registered_key_in_v1(self):
        resp = self.client.get("/v1/provider?key=validkey")
        assert_equals(resp.status_code, 200)

    def test_forbidden_if_unregistered_key_in_v1(self):
        resp = self.client.get("/v1/provider?key=invalidkey")
        assert_equals(resp.status_code, 403)

    def test_importer_post_bibtex(self): 
        bibtex_snippet = """@article{rogers2008affirming,
              title={Affirming Complexity:" White Teeth" and Cosmopolitanism},
              author={Rogers, K.},
              journal={Interdisciplinary Literary Studies},
              year={2008}
            }"""       
        response = self.client.post(
            '/v1/importer/bibtex' + "?key=validkey",
            data=json.dumps({"input": bibtex_snippet}),
            content_type="application/json"
        )
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(response.mimetype, "application/json")
        assert_equals(len(json.loads(response.data)), 1)

        tiid = json.loads(response.data)["products"].keys()[0]
        item = item_module.Item.from_tiid(tiid)
        for biblio in item.biblios:
            if biblio.biblio_name == "authors":
                assert_equals(biblio.biblio_value, "Rogers")


    def test_memberitems_get(self):        
        response = self.client.get('/v1/provider/dryad/memberitems/Otto%2C%20Sarah%20P.?method=sync&key=validkey')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data)["memberitems"], GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")

    def test_memberitems_get_with_nonprinting_character(self):        
        response = self.client.get(u'/v1/provider/dryad/memberitems/Otto\u200e%2C%20Sarah%20P.?method=sync&key=validkey')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data)["memberitems"], GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")

    def test_file_parsing(self):
        datadir = os.path.join(os.path.split(__file__)[0], "../../extras/sample_provider_pages/bibtex")
        path = os.path.join(datadir, "Vision.bib")
        bibtex_str = open(path, "r").read()

    def test_exists(self):
        resp = self.client.get("/v1/provider?key=validkey")
        assert resp

    def test_gets_delicious_static_meta(self):
        resp = self.client.get("/v1/provider?key=validkey")
        md = json.loads(resp.data)
        print md["delicious"]
        assert md["delicious"]['metrics']["bookmarks"]["description"]

    def test_item_post_unknown_tiid(self):
        response = self.client.post('/v1/item/doi/AnIdOfSomeKind/' + "?key=validkey")
        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(json.loads(response.data), u'ok')

    def test_item_post_success(self):
        resp = self.client.post('/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey")
        tiid = json.loads(resp.data)

        response = self.client.get('/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey")
        assert_equals(response.status_code, 210) # 210 created, but not done updating...
        assert_equals(response.mimetype, "application/json")
        saved_item = json.loads(response.data)

        assert_equals([unicode(TEST_DRYAD_DOI)], saved_item["aliases"]["doi"])

    def test_tiid_get(self):
        response = self.client.post(
            '/v1/importer/dois' + "?key=validkey",
            data=json.dumps({"input": TEST_DRYAD_DOI}),
            content_type="application/json"
        )
        created_tiid = json.loads(response.data)["products"].keys()[0]
        print created_tiid

        response = self.client.get('/v1/tiid/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey")
        print response.data
        found_tiid = json.loads(response.data)["tiid"]

        assert_equals(created_tiid, found_tiid)

    def test_item_get_missing_no_create_param_returns_404(self):
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey"
        response = self.client.get(url)
        assert_equals(response.status_code, 404) # created but still updating

    def test_item_get_create_param_makes_new_item(self):
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey&register=true"
        response = self.client.get(url)
        assert_equals(response.status_code, 210) # created and still updating
        item_info = json.loads(response.data)
        assert_equals(item_info["aliases"]["doi"][0], TEST_DRYAD_DOI)

    def test_v1_item_post_success(self):
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey"
        response = self.client.post(url)
        assert_equals(response.status_code, 201)
        assert_equals(json.loads(response.data), "ok")

    def test_item_get_success_realid(self):
        # First put something in
        response = self.client.get('/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey")
        tiid = response.data
        print response
        print tiid

    def test_v1_item_get_success_realid(self):
        # First put something in
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey"
        response_post = self.client.post(url)
        # now check response
        response_get = self.client.get(url)
        assert_equals(response_get.status_code, 210)
        expected = {u'created': u'2012-11-06T19:57:15.937961', u'_rev': u'1-05e5d8a964a0fe9af4284a2a7804815f', u'currently_updating': True, u'metrics': {}, u'last_modified': u'2012-11-06T19:57:15.937961', u'biblio': {u'genre': u'dataset'}, u'_id': u'jku42e6ogs8ghxbr7p390nz8', u'type': u'item', u'aliases': {u'doi': [u'10.5061/dryad.7898']}}
        response_data = json.loads(response_get.data)        
        assert_equals(response_data["aliases"], {u'doi': [TEST_DRYAD_DOI]})

    def test_item_post_unknown_namespace(self):
        response = self.client.post('/v1/item/AnUnknownNamespace/AnIdOfSomeKind/' + "?key=validkey")
        # cheerfully creates items whether we know their namespaces or not.
        assert_equals(response.status_code, 201)

    def test_item_nid_with_bad_character(self):
        url = '/v1/item/doi/10.5061/dryad.' + u'\u200b' + 'j1fd7?key=validkey'
        response_get = self.client.get(url)
        assert_equals(response_get.status_code, 200)

    def test_item_removes_history_by_default(self):
        url = '/v1/item/doi/10.5061/dryad.j1fd7?key=validkey'
        response = self.client.get(url)
        metrics = json.loads(response.data)["metrics"]
        assert_equals(metrics["dryad:total_downloads"]["values"]["raw"], 132)
        assert_equals(
            set(metrics["dryad:total_downloads"]["values"].keys()),
            set(["raw"]) # no raw_history
        )

    def test_item_include_history_param(self):
        url = '/v1/item/doi/10.5061/dryad.j1fd7?key=validkey&include_history=true'
        response = self.client.get(url)

        metrics = json.loads(response.data)["metrics"]
        print (metrics["dryad:total_downloads"])
        assert_equals(
            set(metrics["dryad:total_downloads"]["values"].keys()),
            set(["raw", "raw_history"])
        )

        assert_equals(metrics["dryad:total_downloads"]["values"]["raw_history"].values(), [132, 132, 132])


    def test_post_with_aliases_already_in_db(self):
        items = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        resp = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": items, "title":"mah collection"}),
            content_type="application/json"
        )
        coll = json.loads(resp.data)["collection"]

        new_items = [
            ["doi", "10.123"], # duplicate
            ["doi", "10.124"], # duplicate
            ["doi", "10.999"]  # new
        ]

        resp2 = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": new_items, "title": "mah_collection"}),
            content_type="application/json"
        )
        new_coll = json.loads(resp2.data)["collection"]

        collection_tiid_objects = collection.CollectionTiid.query.all()
        assert_equals(len(collection_tiid_objects), 6)
        assert_equals(len(set([obj.tiid for obj in collection_tiid_objects])), 6)


    def test_collection_post_new_collection(self):
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": self.aliases, "title":"My Title"}),
            content_type="application/json")

        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(response.mimetype, "application/json")
        response_loaded = json.loads(response.data)
        assert_equals(
                set(response_loaded.keys()),
                set(["collection"])
        )
        coll = response_loaded["collection"]
        assert_equals(len(coll["_id"]), 6)
        assert_equals(
            set(coll["alias_tiids"].keys()),
            set([":".join(alias) for alias in self.aliases])
        )

        collection_object = collection.Collection.query.filter_by(cid=coll["_id"]).first()
        assert_items_equal(collection_object.tiids, coll["alias_tiids"].values())
        assert_items_equal([added_item.alias_tuple for added_item in collection_object.added_items], [(unicode(a), unicode(b)) for (a, b) in self.aliases])


    def test_collection_post_new_from_tiids(self):
        tiids = ["123", "456"]
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"tiids": tiids, "title":"My Title"}),
            content_type="application/json")

        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(response.mimetype, "application/json")
        response_loaded = json.loads(response.data)
        assert_equals(
                set(response_loaded.keys()),
                set(["collection"])
        )
        coll = response_loaded["collection"]
        assert_equals(len(coll["_id"]), 6)
        assert_equals(coll["alias_tiids"].keys(), tiids)

        collection_object = collection.Collection.query.filter_by(cid=coll["_id"]).first()
        assert_items_equal(collection_object.tiids, tiids)
        assert_items_equal(collection_object.added_items, [])


    def test_collection_get_with_no_id(self):
        response = self.client.get('/v1/collection/' + "?key=validkey")
        assert_equals(response.status_code, 404)  #Not found

    def test_collection_get(self):
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        collection_id = collection["_id"]
        print collection_id

        resp = self.client.get('/v1/collection/'+collection_id + "?key=validkey")
        assert_equals(resp.status_code, 210)
        collection_data = json.loads(resp.data)
        print collection_data.keys()
        assert_equals(
            set(collection_data.keys()),
            {u'title',
             u'items',
             u'created',
             u'last_modified',
             u'alias_tiids',
             u'_id',
             u'type'}
        )
        assert_equals(len(collection_data["items"]), len(self.aliases))


    def test_get_csv(self):
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        collection_id = collection["_id"]

        resp = self.client.get('/collection/'+collection_id+'.csv')
        print resp
        rows = resp.data.split("\n")
        print rows
        assert_equals(len(rows), 5) # header plus 3 items plus csvDictWriter adds an extra line

    def test_collection_update_puts_items_on_alias_queue(self):
        items = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        resp = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": items, "title":"mah collection"}),
            content_type="application/json"
        )
        coll = json.loads(resp.data)["collection"]
        print coll
        cid = coll["_id"]

        resp = self.client.post(
            "/v1/collection/" + cid + "?key=validkey"
        )
        assert_equals(resp.data, "true")

        # test it is on the redis queue
        response_json = self.r.rpop("aliasqueue")
        print response_json

        response = json.loads(response_json)
        assert_equals(len(response), 3)
        assert_equals(response[1]["doi"][0][0:3], "10.")
        assert_equals(response[2], [])
        

    def test_delete_collection_item(self):
        # make a new collection
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll =  resp["collection"]

        # delete an item.
        tiid_to_delete = coll["alias_tiids"]["doi:10.123"]

        collection_object = collection.Collection.query.filter_by(cid=coll["_id"]).first()
        assert(tiid_to_delete in collection_object.tiids)

        r = self.client.delete(
            "/v1/collection/{id}/items?api_admin_key={key}".format(
                id=coll["_id"], 
                key=os.getenv("API_KEY")),
            data=json.dumps({"tiids": [tiid_to_delete]}),
            content_type="application/json"
        )

        collection_object = collection.Collection.query.filter_by(cid=coll["_id"]).first()
        assert_equals(len(collection_object.tiids), 2)

        assert(tiid_to_delete not in collection_object.tiids)


    def test_add_collection_item_through_tiids(self):
        # make two items through an importer
        response = self.client.post(
            '/v1/importer/dois' + "?key=validkey",
            data=json.dumps({"input": TEST_DRYAD_DOI + "\n" + TEST_PLOS_DOI}),
            content_type="application/json"
        )
        created_tiids = json.loads(response.data)["products"].keys()
        print created_tiids

        # make a new collection using the first item
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"tiids": [created_tiids[0]], "title":"My Title"}),
            content_type="application/json")

        coll = json.loads(response.data)["collection"]
        cid = coll["_id"]

        # now add the other item
        r = self.client.put(
            "/v1/collection/{id}/items?api_admin_key={key}".format(
                id=cid, 
                key=os.getenv("API_KEY")),
            data=json.dumps({"tiids": [created_tiids[1]]}),
            content_type="application/json"
        )

        changed_coll = collection.Collection.query.filter_by(cid=cid).first()
        print changed_coll

        # we added a new item
        print changed_coll.tiids
        assert_equals(changed_coll.tiids, created_tiids)


    def test_add_collection_item_through_aliases(self):        
        # make a new collection
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll = resp["collection"]

        alias_list = []
        alias_list.append(["doi", "10.new"])

        r = self.client.put(
            "/v1/collection/{id}/items?api_admin_key={key}".format(
                id=coll["_id"], 
                key=os.getenv("API_KEY")),
            data=json.dumps({"aliases": alias_list}),
            content_type="application/json"
        )

        changed_coll = collection.Collection.query.filter_by(cid=coll["_id"]).first()
        print changed_coll

        # we added a new item
        assert_equals(len(changed_coll.tiids), 4)


    def test_change_collection_requires_key(self):

        # make a new collection
        response = self.client.post(
            '/v1/collection' + "?key=validkey",
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll =  resp["collection"]

        alias_list = []
        alias_list.append(["doi", "10.new"])

        # 403 Forbidden if wrong edit key
        r = self.client.put(
            "/v1/collection/{id}/items?api_admin_key={key}".format(
                id=coll["_id"], 
                key="wrong!"),
            data=json.dumps({"aliases": alias_list}),
            content_type="application/json"
        )
        assert_equals(r.status_code, 403)

        # 403 Bad Request if no edit key
        r = self.client.put(
            "/v1/collection/{id}/items".format(id=coll["_id"]),
            data=json.dumps({"aliases": alias_list}),
            content_type="application/json"
        )
        assert_equals(r.status_code, 403)

        # get the collection out the db and make sure nothing's changed
        changed_coll = collection.Collection.query.filter_by(cid=coll["_id"]).first()

        assert_equals(changed_coll.title, "mah collection")


    def test_tiid_get_tiids_for_multiple_known_aliases(self):
        # create two new items with the same plos alias
        first_plos_create_tiid_resp = self.client.post('/v1/item/doi/' +
                quote_plus(TEST_PLOS_DOI) + "?key=validkey")
        first_plos_create_tiid = json.loads(first_plos_create_tiid_resp.data)

        second_plos_create_tiid_resp = self.client.post('/v1/item/doi/' +
                quote_plus(TEST_PLOS_DOI) + "?key=validkey")
        second_plos_create_tiid = json.loads(second_plos_create_tiid_resp.data)

        # check that the tiid lists are the same
        assert_equals(first_plos_create_tiid, second_plos_create_tiid)


    def test_inbox(self):
        example_payload = {
               "headers": {
                   "To": "7be5eb5001593217143f@cloudmailin.net",
                   "From": "Google Scholar Alerts <scholaralerts-noreply@google.com>",
                   "Date": "Thu, 21 Feb 2013 20:00:13 +0000",
                   "Subject": "Confirm your Google Scholar Alert"
               },
               "plain": "Google received a request to start sending Scholar Alerts to  \n7be5eb5001593217143f@cloudmailin.net for the query:\nNew articles in Jonathan A. Eisen's profile\n\nClick to confirm this request:\nhttp://scholar.google.ca/scholar_alerts?update_op=confirm_alert&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net\n\nClick to cancel this request:\nhttp://scholar.google.ca/scholar_alerts?view_op=cancel_alert_options&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net\n\nThanks,\nThe Google Scholar Team",
            }

        response = self.client.post(
            "/v1/inbox?key=validkey",
            data=json.dumps(example_payload),
            content_type="application/json"
        )
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data), {u'subject': u'Confirm your Google Scholar Alert'})


    def test_new_api_user(self):
        # the api call needs the admin password
        self.test_api_user_meta["password"] = os.getenv("API_KEY")

        response = self.client.post(
            '/v1/key?key=validkey',
            data=json.dumps(self.test_api_user_meta),
            content_type="application/json"
        )
        print response.data
        resp_loaded = json.loads(response.data)
        assert_equals(resp_loaded["api_key"].split("-")[0], self.test_api_user_meta["prefix"].lower())


    def test_item_post_known_tiid(self):
        response = self.client.post('/v1/item/doi/IdThatAlreadyExists/' + "?key=validkey")
        print response
        print "here is the response data: " + response.data

        # FIXME should check and if already exists return 200
        # right now this makes a new item every time, creating many dups
        assert_equals(response.status_code, 201)
        assert_equals(json.loads(response.data), u'ok')





