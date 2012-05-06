import unittest, json, uuid
from copy import deepcopy
from urllib import quote_plus
from nose.tools import nottest, assert_equals
from BeautifulSoup import BeautifulSoup

from totalimpact import api, dao
from totalimpact.config import Configuration
from totalimpact.providers.dryad import Dryad
import os, yaml


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
    "item_tiids": ["origtiid1", "origtiid2"] 
}""")
COLLECTION_SEED_MODIFIED = deepcopy(COLLECTION_SEED)
COLLECTION_SEED_MODIFIED["item_tiids"] = TEST_COLLECTION_TIID_LIST_MODIFIED

sample_item_loc = os.path.join(
    os.path.split(__file__)[0],
    '../data/couch_docs/article.yml')
f = open(sample_item_loc, "r")
ARTICLE_ITEM = yaml.load(f.read())

rendered_article_loc = os.path.join(
    os.path.split(__file__)[0],
    '../rendered_views/article.html')
RENDERED_ARTICLE = open(rendered_article_loc, "r").read()

def MOCK_member_items(self, a, b):
    return(GOLD_MEMBER_ITEM_CONTENT) 


class ApiTester(unittest.TestCase):

    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True
        self.client = self.app.test_client()
        # setup the database
        self.testing_db_name = "api_test"
        self.app.config["DB_NAME"] = self.testing_db_name
        self.d = dao.Dao(
            self.app.config["DB_NAME"],
            self.app.config["DB_URL"],
            self.app.config["DB_USERNAME"], 
            self.app.config["DB_PASSWORD"])

        self.d.create_new_db_and_connect(self.testing_db_name)

class TestMemberItems(ApiTester):

    def setUp(self): 
        super(TestMemberItems, self).setUp()
        # Mock out relevant methods of the Dryad provider
        self.orig_Dryad_member_items = Dryad.member_items
        Dryad.member_items = MOCK_member_items

    def tearDown(self):
        Dryad.member_items = self.orig_Dryad_member_items

    def test_memberitems_get(self):
        response = self.client.get('/provider/dryad/memberitems?query=Otto%2C%20Sarah%20P.&type=author')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data), GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")

class TestTiid(ApiTester):

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
        response = self.client.get('/item/' + str(uuid.uuid4()))
        assert_equals(response.status_code, 404)  # Not Found

    def test_item_post_known_tiid(self):
        response = self.client.post('/item/doi/IdThatAlreadyExists/')
        print response
        print response.data

        # FIXME should check and if already exists return 200
        # right now this makes a new item every time, creating many dups
        assert_equals(response.status_code, 201)
        assert_equals(len(json.loads(response.data)), 32)
        assert_equals(response.mimetype, "application/json")

    def test_item_get_unknown_tiid(self):
        # pick a random ID, very unlikely to already be something with this ID
        response = self.client.get('/item/' + str(uuid.uuid4()))
        assert_equals(response.status_code, 404)  # Not Found

class TestItem(ApiTester):

    def test_item_post_unknown_tiid(self):
        response = self.client.post('/item/doi/AnIdOfSomeKind/')
        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(len(json.loads(response.data)), 32)
        assert_equals(response.mimetype, "application/json")

    def test_item_get_success_fakeid(self):        
        
        # First put something in
        response_create = self.client.post('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = response_create.data
        print tiid

        # Now try to get it out
        # Strip off leading and trailing quotation marks
        tiid = tiid.replace('"', '')
        response = self.client.get('/item/' + tiid)
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(
            set(json.loads(response.data).keys()),
            set([u'aliases', u'biblio', u'created', u'id', u'last_modified',
                u'last_requested', u'metrics'])
            )
        assert_equals(response.mimetype, "application/json")

    def test_item_post_urldecodes(self):
        resp = self.client.post('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = resp.data.replace('"', '')

        resp = self.client.get('/item/' + tiid)
        saved_item = json.loads(resp.data)

        assert_equals([unicode(TEST_DRYAD_DOI)], saved_item["aliases"]["doi"])

    def test_item_get_success_realid(self):
        # First put something in
        response = self.client.get('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = response.data
        print response
        print tiid

    def test_item_post_unknown_namespace(self):
        response = self.client.post('/item/AnUnknownNamespace/AnIdOfSomeKind/')
        assert_equals(response.status_code, 501)  # "Not implemented"

    def test_returns_json_default(self): 
        # upload the item manually...there's no api call to do this.
        print self.d.save(ARTICLE_ITEM)
        response = self.client.get('/item/' + ARTICLE_ITEM['id'])
        assert_equals(response.headers[0][1], 'application/json')

    def test_returns_html_mimetype(self):
        print self.d.save(ARTICLE_ITEM) 
        response = self.client.get('item/{0}.html'.format(ARTICLE_ITEM['id']))
        assert_equals(response.headers[0][1], 'text/html') 

    def test_returns_html_view(self):
        print self.d.save(ARTICLE_ITEM)
        response = self.client.get('item/{0}.html'.format(ARTICLE_ITEM['id']))

        # parsing makes debugging much easier...impossible   to visually compare
        # the raw markup strings when not pretty-printed.
        returned = BeautifulSoup(response.data)
        expected = BeautifulSoup(RENDERED_ARTICLE)

        assert returned.find('h4') is not None
        assert_equals(returned('h4'), expected('h4'))     

        assert returned.find('div', "biblio") is not None
        assert_equals(
            returned.find('div', "biblio").soup,
            expected.find('div', "biblio").soup)

        # in progress... 

        assert returned.find('ul', "metrics") is not None


        assert_equals(
            returned.find('ul', "metrics").soup,
            expected.find('ul', "metrics").soup)


class TestItems(ApiTester):

    def test_post_with_multiple_items(self):
        items = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        resp = self.client.post(
            '/items',
            data=json.dumps(items),
            content_type="application/json"
        )
        dois = []
        for tiid in json.loads(resp.data):
            doc = self.d.get(tiid)
            dois.append(doc['aliases']['doi'][0])

        expected_dois = [i[1] for i in items]
        assert_equals(set(expected_dois), set(dois))






class TestCollection(ApiTester):

    def test_collection_post_already_exists(self):
        response = self.client.post('/collection/' + TEST_COLLECTION_ID)
        assert_equals(response.status_code, 405)  # Method Not Allowed

    def test_collection_post_new_collection(self):
        response = self.client.post(
            '/collection',
            data=json.dumps({"items": TEST_COLLECTION_TIID_LIST, "title":"My Title"}),
            content_type="application/json")

        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(response.mimetype, "application/json")
        response_loaded = json.loads(response.data)
        assert_equals(
                set(response_loaded.keys()),
                set([u'created', u'item_tiids', u'last_modified', u'id', u'title']))
        assert_equals(len(response_loaded["id"]), 6)

    def test_collection_put_updated_collection(self):

        # Put in an item.  Could mock this out in the future.
        response = self.client.post('/collection',
                data=json.dumps({"items": TEST_COLLECTION_TIID_LIST, "title":"My Title"}),
                content_type="application/json")
        response_loaded = json.loads(response.data)
        new_collection_id = response_loaded["id"]

        # put the new collection stuff
        response = self.client.put('/collection/' + new_collection_id,
                data=json.dumps(COLLECTION_SEED_MODIFIED),
                content_type="application/json")
        print response
        print response.data
        assert_equals(response.status_code, 200)  #updated
        assert_equals(response.mimetype, "application/json")
        response_loaded = json.loads(response.data)
        assert_equals(
                set(response_loaded.keys()),
                set([u'created', u'collection_name', u'item_tiids', u'last_modified',
                    u'owner', u'id'])
                )
        assert_equals(response_loaded["item_tiids"],
            COLLECTION_SEED_MODIFIED["item_tiids"])

    def test_collection_put_empty_payload(self):
        response = self.client.put('/collection/' + TEST_COLLECTION_ID)
        assert_equals(response.status_code, 404)  #Not found

    def test_collection_delete_with_no_id(self):
        response = self.client.delete('/collection/')
        assert_equals(response.status_code, 404)  #Not found




    def test_collection_get_with_no_id(self):
        response = self.client.get('/collection/')
        assert_equals(response.status_code, 404)  #Not found

class TestApi(ApiTester):

    def setUp(self):

        super(TestApi, self).setUp()


    def test_collection_delete_deletes(self):
        # Put in an item.  Could mock this out in the future.
        response = self.client.post('/collection',
                data=json.dumps({"items": TEST_COLLECTION_TIID_LIST, "title":"My Title"}),
                content_type="application/json")
        response_loaded = json.loads(response.data)
        new_collection_id = response_loaded["id"]

        # it's in there
        response1 = self.client.get('/collection/' + new_collection_id)
        assert_equals(response1.status_code, 200) #OK

        # lightning bolt! lightning bolt!
        response = self.client.delete('/collection/' + new_collection_id)
        assert_equals(response.status_code, 204)

        # is it gone?
        response2 = self.client.get('/collection/' + new_collection_id)
        assert_equals(response2.status_code, 404)  #Not found
        
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
        assert_equals(plos_create_tiid, plos_lookup_tiids[0])

    def test_tiid_get_tiids_for_multiple_known_aliases(self):
        # create two new items with the same plos alias
        first_plos_create_tiid_resp = self.client.post('/item/doi/' + 
                quote_plus(PLOS_TEST_DOI))
        first_plos_create_tiid = json.loads(first_plos_create_tiid_resp.data)

        second_plos_create_tiid_resp = self.client.post('/item/doi/' + 
                quote_plus(PLOS_TEST_DOI))
        second_plos_create_tiid = json.loads(second_plos_create_tiid_resp.data)

        # retrieve the plos tiid using tiid api
        plos_lookup_tiid_resp = self.client.get('/tiid/doi/' + 
                quote_plus(PLOS_TEST_DOI))
        assert_equals(plos_lookup_tiid_resp.status_code, 303)  
        plos_lookup_tiids = json.loads(plos_lookup_tiid_resp.data)

        # check that the tiid lists are the same
        assert_equals(sorted(plos_lookup_tiids), 
            sorted([first_plos_create_tiid, second_plos_create_tiid]))
