import unittest, json, uuid
from copy import deepcopy
from urllib import quote_plus
from nose.tools import assert_equals

from totalimpact import app, dao, views
from totalimpact.providers.dryad import Dryad
import os


TEST_DRYAD_DOI = "10.5061/dryad.7898"
PLOS_TEST_DOI = "10.1371/journal.pone.0004803"
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


api_items_loc = os.path.join(
    os.path.split(__file__)[0],
    '../data/items.json')
API_ITEMS_JSON = json.loads(open(api_items_loc, "r").read())

def MOCK_member_items(self, query_string, url=None, cache_enabled=True):
    return(GOLD_MEMBER_ITEM_CONTENT)

# ensures that all the functions in the views.py module will use a local db,
# which we can in turn use for these unit tests.
mydao = views.set_db("http://localhost:5984", os.getenv("CLOUDANT_DB"))


class ViewsTester(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))

        #setup api test client
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

class DaoTester(unittest.TestCase):
    def test_dao(self):
        assert_equals(mydao.db.name, os.getenv("CLOUDANT_DB"))


class TestMemberItems(ViewsTester):

    def setUp(self): 
        super(TestMemberItems, self).setUp()
        # Mock out relevant methods of the Dryad provider
        self.orig_Dryad_member_items = Dryad.member_items
        Dryad.member_items = MOCK_member_items

    def tearDown(self):
        Dryad.member_items = self.orig_Dryad_member_items

    def test_memberitems_get(self):
        response = self.client.get('/provider/dryad/memberitems/Otto%2C%20Sarah%20P.?method=sync')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data)["memberitems"], GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")


class TestProvider(ViewsTester):

        def test_exists(self):
            resp = self.client.get("/provider")
            assert resp

        def test_gets_delicious_static_meta(self):
            resp = self.client.get("/provider")
            md = json.loads(resp.data)
            print md["delicious"]
            assert md["delicious"]['metrics']["bookmarks"]["description"]



class TestItem(ViewsTester):

    def test_item_post_unknown_tiid(self):
        response = self.client.post('/item/doi/AnIdOfSomeKind/')
        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(len(json.loads(response.data)), 24)
        assert_equals(response.mimetype, "application/json")

    def test_item_post_success(self):
        resp = self.client.post('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = json.loads(resp.data)

        response = self.client.get('/item/' + tiid)
        assert_equals(response.status_code, 210) # 210 created, but not done updating...
        assert_equals(response.mimetype, "application/json")
        saved_item = json.loads(response.data)

        assert_equals([unicode(TEST_DRYAD_DOI)], saved_item["aliases"]["doi"])

    def test_item_get_success_realid(self):
        # First put something in
        response = self.client.get('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = response.data
        print response
        print tiid

    def test_item_post_unknown_namespace(self):
        response = self.client.post('/item/AnUnknownNamespace/AnIdOfSomeKind/')
        # cheerfully creates items whether we know their namespaces or not.
        assert_equals(response.status_code, 201)


class TestItems(ViewsTester):
    def test_post_with_aliases_already_in_db(self):
        items = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        resp = self.client.post(
            '/collection',
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
            '/collection',
            data=json.dumps({"aliases": new_items, "title": "mah_collection"}),
            content_type="application/json"
        )
        new_coll = json.loads(resp2.data)["collection"]

        # 3 new items + 1 new item + 1 design doc + 2 collections
        assert_equals(self.d.db.info()["doc_count"], 7)



class TestCollection(ViewsTester):

    def setUp(self):
        self.aliases = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        super(TestCollection, self).setUp()

    def test_collection_post_new_collection(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"My Title"}),
            content_type="application/json")

        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(response.mimetype, "application/json")
        response_loaded = json.loads(response.data)
        assert_equals(
                set(response_loaded.keys()),
                set(["collection", "key"])
        )
        coll = response_loaded["collection"]
        assert_equals(len(coll["_id"]), 6)
        assert_equals(
            set(coll["alias_tiids"].keys()),
            set([":".join(alias) for alias in self.aliases])
        )

    def test_new_collection_includes_key(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"My Title"}),
            content_type="application/json"
        )
        print response.data
        resp_loaded = json.loads(response.data)
        assert_equals(resp_loaded.keys(), ["key", "collection"])


    def test_collection_get_with_no_id(self):
        response = self.client.get('/collection/')
        assert_equals(response.status_code, 404)  #Not found

    def test_make_csv_rows(self):
        csv = views.make_csv_rows(API_ITEMS_JSON)
        expected = 'tiid,title,doi,dryad:most_downloaded_file,dryad:package_views,dryad:total_downloads,mendeley:groups,mendeley:readers,plosalm:crossref,plosalm:html_views,plosalm:pdf_views,plosalm:pmc_abstract,plosalm:pmc_figure,plosalm:pmc_full-text,plosalm:pmc_pdf,plosalm:pmc_supp-data,plosalm:pmc_unique-ip,plosalm:pubmed_central,plosalm:scopus,wikipedia:mentions\r\nf2b45fcab1da11e19199c8bcc8937e3f,"Tumor-Immune Interaction, Surgical Treatment, and Cancer Recurrence in a Mathematical Model of Melanoma",10.1371/journal.pcbi.1000362,,,,1,13,7,2075,484,29,13,232,113,0,251,2,11,\r\nc1eba010b1da11e19199c8bcc8937e3f,"data from: comparison of quantitative and molecular genetic variation of native vs. invasive populations of purple loosestrife (lythrum salicaria l., lythraceae)",10.5061/dryad.1295,70,537,114,,,,,,,,,,,,,,\r\nc202754cb1da11e19199c8bcc8937e3f,Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article,10.1371/journal.pcbi.1000361,,,,4,52,13,11521,1097,70,39,624,149,6,580,12,19,1\r\nf2dc3f36b1da11e19199c8bcc8937e3f,Design Principles for Riboswitch Function,10.1371/journal.pcbi.1000363,,,,4,57,16,3361,1112,37,54,434,285,41,495,9,19,\r\n'
        assert_equals(csv, expected)

    def test_get_csv(self):

        response = self.client.post(
            '/collection',
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

    def test_collection_get(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        collection_id = collection["_id"]

        resp = self.client.get('/collection/'+collection_id)
        assert_equals(resp.status_code, 210)
        collection_data = json.loads(resp.data)
        assert_equals(
            set(collection_data.keys()),
            {u'title',
             u'items',
             u'_rev',
             u'created',
             u'last_modified',
             u'ip_address',
             u'_id',
             u'key_hash',
             u'owner',
             u'type'}
        )
        assert_equals(len(collection_data["items"]), len(self.aliases))


    def test_collection_update_puts_items_on_update_queue(self):
        # put some stuff in the collection:
        # put some items in the db
        for doc in mydao.db.update([
                {"_id":"larry"},
                {"_id":"curly"},
                {"_id":"moe"}
        ]):
            pass # no need to do anything, just put 'em in couch.

        collection = {
            "_id":"123",
            "alias_tiids": {"doi:abc":"larry", "doi:def":"moe", "ghi":"curly"}
            }
        mydao.save(collection)
        resp = self.client.post(
            "/collection/123"
        )
        assert_equals(resp.data, "true")

        larry = mydao.get("larry")
        print larry
        # super hacky way to test for iso date string
        assert_equals(larry["needs_aliases"][0:4], "2012")

    def test_collection_owner_set_at_creation(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        assert_equals(collection["owner"], "plato")

    def test_change_collection(self):

        # make a new collection
        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll =  resp["collection"]
        key =  resp["key"]

        # change some stuff
        coll["owner"] = "aristotle"
        coll["title"] = "plato sux lol"

        r = self.client.put(
            "/collection/{id}?key={key}".format(id=coll["_id"], key=key),
            data=json.dumps(coll),
            content_type="application/json"
        )

        # get the collection out the db and see if it's the same one
        changed_coll = self.d.get(coll["_id"])
        assert_equals(changed_coll["title"], "plato sux lol")
        assert_equals(changed_coll["owner"], "aristotle")


    def test_change_collection_requires_key(self):

        # make a new collection
        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll =  resp["collection"]
        key =  resp["key"]

        # change some stuff
        coll["owner"] = "aristotle"
        coll["title"] = "plato sux lol"

        # 403 Forbidden if wrong key
        r = self.client.put(
            "/collection/{id}?key={key}".format(id=coll["_id"], key="bad key"),
            data=json.dumps(coll),
            content_type="application/json"
        )
        assert_equals(r.status_code, 403)

        # 404 Bad Request if no key
        r = self.client.put(
            "/collection/{id}".format(id=coll["_id"]),
            data=json.dumps(coll),
            content_type="application/json"
        )
        assert_equals(r.status_code, 404)

        # get the collection out the db and make sure nothing's changed
        changed_coll = self.d.get(coll["_id"])
        assert_equals(changed_coll["title"], "mah collection")
        assert_equals(changed_coll["owner"], "plato")


class TestApi(ViewsTester):

    def setUp(self):
        super(TestApi, self).setUp()

    def tearDown(self):
        pass

    def test_clean_id(self):
        nid = u"10.1000/\u200bna\tture "
        response = views.clean_id(nid)
        assert_equals(response, u'10.1000/nature')

    def test_tiid_get_with_unknown_alias(self):
        # try to retrieve tiid id for something that doesn't exist yet
        plos_no_tiid_resp = self.client.get('/tiid/doi/' +
                quote_plus(PLOS_TEST_DOI))
        assert_equals(plos_no_tiid_resp.status_code, 404)  # Not Found


    def test_tiid_get_with_known_alias(self):
        # create new plos item from a doi
        plos_create_tiid_resp = self.client.post('/item/doi/' +
                quote_plus(PLOS_TEST_DOI))
        plos_create_tiid = json.loads(plos_create_tiid_resp.data)

        # retrieve the plos tiid using tiid api
        plos_lookup_tiid_resp = self.client.get('/tiid/doi/' +
                quote_plus(PLOS_TEST_DOI))
        assert_equals(plos_lookup_tiid_resp.status_code, 303)
        plos_lookup_tiids = json.loads(plos_lookup_tiid_resp.data)

        # check that the tiids are the same
        assert_equals(plos_create_tiid, plos_lookup_tiids)

    def test_tiid_get_tiids_for_multiple_known_aliases(self):
        # create two new items with the same plos alias
        first_plos_create_tiid_resp = self.client.post('/item/doi/' +
                quote_plus(PLOS_TEST_DOI))
        first_plos_create_tiid = json.loads(first_plos_create_tiid_resp.data)

        second_plos_create_tiid_resp = self.client.post('/item/doi/' +
                quote_plus(PLOS_TEST_DOI))
        second_plos_create_tiid = json.loads(second_plos_create_tiid_resp.data)

        # check that the tiid lists are the same
        assert_equals(first_plos_create_tiid, second_plos_create_tiid)



class TestTiid(ViewsTester):

    def test_tiid_post(self):
        # POST isn't supported
        response = self.client.post('/tiid/Dryad/NotARealId')
        assert_equals(response.status_code, 405)  # Method Not Allowed

    def test_tiid_post(self):
        # POST isn't supported
        response = self.client.post('/tiid/Dryad/NotARealId')
        assert_equals(response.status_code, 405)  # Method Not Allowed

    def test_item_get_unknown_tiid(self):
        # pick a random ID, very unlikely to already be something with this ID
        response = self.client.get('/item/' + str(uuid.uuid1()))
        assert_equals(response.status_code, 404)  # Not Found

    def test_item_post_known_tiid(self):
        response = self.client.post('/item/doi/IdThatAlreadyExists/')
        print response
        print "here is the response data: " + response.data

        # FIXME should check and if already exists return 200
        # right now this makes a new item every time, creating many dups
        assert_equals(response.status_code, 201)
        assert_equals(len(json.loads(response.data)), 24)
        assert_equals(response.mimetype, "application/json")

    def test_item_get_unknown_tiid(self):
        # pick a random ID, very unlikely to already be something with this ID
        response = self.client.get('/item/' + str(uuid.uuid1()))
        assert_equals(response.status_code, 404)  # Not Found

class TestUser(ViewsTester):
    def test_create(self):
        resp = self.client.post(
            "/user/horace@rome.it",
            data=json.dumps({"key": "password"}),
            content_type="application/json"
        )
        assert_equals("horace@rome.it", json.loads(resp.data)["_id"])

    def test_create_if_already_exists(self):
        resp = self.client.post(
            "/user/ovid@rome.it",
            data=json.dumps({"key": "password"}),
            content_type="application/json"
        )
        resp2 = self.client.post(
            "/user/ovid@rome.it",
            data=json.dumps({"key": "another password"}),
            content_type="application/json"
        )
        assert_equals(409, resp2.status_code)

    def test_create_without_key_in_post_body(self):
        resp = self.client.post(
            "/user/pliny@rome.it",
            data='""',
            content_type="application/json"
        )
        assert_equals(400, resp.status_code)

#    def test_create_with_colls(self):
#        resp = self.client.post(
#            "/user/pliny@rome.it",
#            data=json.loads(["cid1", "cid2"]),
#            content_type="application/json"
#        )
#        assert_equals(["cid1", "cid2"], json.loads(resp.data)["colls"])

    def test_get_user_doesnt_exist(self):
        resp = self.client.get("/user/test@foo.com")
        assert_equals(resp.status_code, 404)

    def test_get_user(self):
        self.client.post(
            "/user/catullus@rome.it",
            data=json.dumps({"key": "passwordhash", "email": "e"}),
            content_type="application/json"
            )

        resp = self.client.get("/user/catullus@rome.it?key=passwordhash")
        resp_dict = json.loads(resp.data)
        print resp_dict

        assert_equals(resp_dict["_id"], "catullus@rome.it")

    def test_update_user(self):

        # create the user
        self.client.post(
            "/user/catullus@rome.it",
            data=json.dumps({"key": "passwordhash", "email": "e"}),
            content_type="application/json"
            )

        # get the new user and add a coll
        resp = self.client.get("/user/catullus@rome.it?key=passwordhash")
        user = json.loads(resp.data)
        user["colls"] = ["cid:123"]

        # put the new, modified user in the db
        res = self.client.put(
            "/user/catullus@rome.it",
            data=json.dumps(user),
            content_type="application/json"
        )

        returned_user = json.loads(res.data)
        assert_equals(returned_user["_id"], "catullus@rome.it")

        # get the user out again, and check to see if it was modified
        resp = self.client.get("/user/catullus@rome.it?key=passwordhash")
        user = json.loads(resp.data)
        assert_equals(user["colls"], ["cid:123"])





