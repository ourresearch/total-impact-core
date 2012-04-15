from nose.tools import raises, assert_equals, nottest
import os, unittest, json, time
from test.mocks import MockDao
from copy import deepcopy

from totalimpact import models
from totalimpact import dao, api

COLLECTION_DATA = {
    "id": "uuid-goes-here",
    "collection_name": "My Collection",
    "owner": "abcdef",
    "created": 1328569452.406,
    "last_modified": 1328569492.406,
    "item_tiids": ["origtiid1", "origtiid2"] 
    }

ALIAS_DATA = {
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
    }

ALIAS_CANONICAL_DATA = {
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
    }

SNAP_DATA = {
    "id": "mendeley:readers",
    "value": 16,
    "created": 1233442897.234,
    "last_modified": 1328569492.406,
    "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
    "static_meta": {
        "display_name": "readers",
        "provider": "Mendeley",
        "provider_url": "http://www.mendeley.com/",
        "description": "Mendeley readers: the number of readers of the article",
        "icon": "http://www.mendeley.com/favicon.ico",
        "category": "bookmark",
        "can_use_commercially": "0",
        "can_embed": "1",
        "can_aggregate": "1",
        "other_terms_of_use": "Must show logo and say 'Powered by Santa'"
        }
    }

METRICS_DATA = {
    "provider_name": "plos", 
    "metric_name": "html_views",
    "ignore": False,
    "metric_snaps": {},
    "latest_snap": None
}

METRICS_DATA2 = {
    "provider_name": "plos",
    "metric_name": "pdf_views",
    "ignore": False,
    "metric_snaps": {},
    "latest_snap": None
}


BIBLIO_DATA = {
        "title": "An extension of de Finetti's theorem", 
        "journal": "Advances in Applied Probability", 
        "author": [
            "Pitman, J"
            ], 
        "collection": "pitnoid", 
        "volume": "10", 
        "id": "p78",
        "year": "1978",
        "pages": "268 to 270"
    }


ITEM_DATA = {
    "_id": "123",
    "_rev": "456",
    "created": 1330260456.916,
    "last_modified": 12414214.234,
    "last_requested": 124141245.234, 
    "aliases": ALIAS_DATA,
    "metrics": [METRICS_DATA, METRICS_DATA2],
    "biblio": BIBLIO_DATA
}
    
TEST_DB_NAME = "test_models"


class TestSaveable():
    def setUp(self):
        pass

    def test_id_gets_set(self):
        s = models.Saveable()
        assert_equals(len(s.id), 32)

        s2 = models.Saveable(id="123")
        assert_equals(s2.id, "123")

    def test_as_dict(self):
        s = models.Saveable()
        s.foo = "a var"
        s.bar = "another var"
        assert_equals(s.as_dict()['foo'], "a var")

    @nottest
    def test_as_dict_recursive(self):
        s = models.Saveable()
        class TestObj:
            pass
        
        class TestObj2:
            pass
        
        foo =  TestObj()
        foo.bar = "I'm in foo!"
        s.my_list = []
        s.my_list.append(foo)
        assert_equals(s.as_dict()['my_list'][0]['bar'], foo.bar)



class TestItemFactory():

    def setUp(self):
        pass

    def test_make_new(self):
        '''create an item from scratch.'''
        factory = models.ItemFactory("not a dao")
        item = factory.make()
        assert_equals(len(item.id), 32)
        assert item.created < time.time

    def test_make_from_db(self):
        dao = MockDao()
        dao.setResponses([ITEM_DATA])

        factory = models.ItemFactory(dao)
        item = factory.make("123")
        print item.as_dict() 

        assert_equals(item.as_dict()["aliases"], ITEM_DATA["aliases"])

'''
class TestItem():

    def setUp(self):
        self.d = dao.Dao(TEST_DB_NAME)
        
        self.d.create_new_db_and_connect(TEST_DB_NAME)
        self.d.get = lambda id: ITEM_DATA
        def fake_save(data, id):
            self.input = data
        self.d.update_item = fake_save

        self.providers = api.providers

    def test_new_testing_class(self):
        assert True

    def test_mock_dao(self):
        assert_equals(self.d.get("123"), ITEM_DATA)

    def ITEM_DATA_init(self):
        i = models.Item(self.d)
        assert_equals(len(i.id), 32) # made a uuid, yay

    def ITEM_DATA_load(self):
        i = models.Item(self.d, id="123")
        i.load()
        assert_equals(i.aliases.as_dict(), ALIAS_CANONICAL_DATA)
        assert_equals(i.created, ITEM_DATA["created"])

    @raises(LookupError)
    def test_load_with_nonexistant_item_fails(self):
        i = models.Item(id="123")
        self.d.get = lambda id: None # that item doesn't exist in the db
        i.load()

    def ITEM_DATA_save(self):
        i = models.Item(self.d, id="123")

        # load all the values from the item_DATA into the test item.
        for key in ITEM_DATA:
            setattr(i, key, ITEM_DATA[key])
        i.save()

        assert_equals(i.aliases, ALIAS_DATA)

        seed = deepcopy(ITEM_DATA)
        seed["_id"] = "123"
        # the fake dao puts the doc-to-save in the self.input var.
        assert_equals(self.input, seed)
'''

@nottest
class TestCollection():

    def setUp(self):        
        self.d = dao.Dao(TEST_DB_NAME)
        self.d.create_new_db_and_connect(TEST_DB_NAME)

    def test_mock_dao(self):
        self.d.get = lambda id: deepcopy(COLLECTION_DATA)
        assert_equals(self.d.get("SomeCollectionId"), COLLECTION_DATA)

    def COLLECTION_DATA_init(self):
        c = models.Collection(self.d)
        assert_equals(len(c.id), 32) # made a uuid, yay

    def COLLECTION_DATA_add_items(self):
        c = models.Collection(self.d, seed=deepcopy(COLLECTION_DATA))
        c.add_items(["newtiid1", "newtiid2"])
        assert_equals(c.item_ids(), [u'origtiid1', u'origtiid2', 'newtiid1', 'newtiid2'])

    def COLLECTION_DATA_remove_item(self):
        c = models.Collection(self.d, seed=deepcopy(COLLECTION_DATA))
        c.remove_item("origtiid1")
        assert_equals(c.item_ids(), ["origtiid2"])

    def COLLECTION_DATA_load(self):
        self.d.get = lambda id: deepcopy(COLLECTION_DATA)
        c = models.Collection(self.d, id="SomeCollectionId")
        c.load()
        assert_equals(c.collection_name, "My Collection")
        assert_equals(c.item_ids(), [u'origtiid1', u'origtiid2'])

    @raises(LookupError)
    def test_load_with_nonexistant_collection_fails(self):
        self.d.get = lambda id: None # that item doesn't exist in the db
        c = models.Collection(self.d, id="AnUnknownCollectionId")
        c.load()

    def COLLECTION_DATA_save(self):
        # this fake save method puts the doc-to-save in the self.input variable
        def fake_save(data, id):
            self.input = data
        self.d.update_item = fake_save

        c = models.Collection(self.d)

        # load all the values from the item_DATA into the test item.
        for key in COLLECTION_DATA:
            setattr(c, key, COLLECTION_DATA[key])
        c.save()

        seed = deepcopy(COLLECTION_DATA)
        # the dao changes the contents to give the id variable the leading underscore expected by couch
        seed["_id"] = seed["id"]
        del(seed["id"])

        # check to see if the fake save method did in fact "save" the collection as expected
        assert_equals(self.input, seed)


class TestMetricSnap(unittest.TestCase):
    pass

class TestMetrics(unittest.TestCase):


    def setUp(self):
        self.m = models.Metrics("plos", "html_views")

    def test_init(self):
        assert len(self.m.metric_snaps) == 0
        assert_equals(self.m.ignore, False )

    def test_add_metric_snap(self):
        start_time = time.time()

        snap1 = deepcopy(SNAP_DATA)
        hash = self.m.add_metric_snap(snap1)

        assert_equals(len(hash), 32)
        assert_equals(self.m.metric_snaps[hash], snap1)
        assert_equals(len(self.m.metric_snaps), 1)
        assert_equals(self.m.latest_snap["value"], snap1["value"])

        # the we've changed something, so the last_modified value should change
        assert  self.m.last_modified > start_time

        # let's try adding a new snap; this has a new value, so it'll get stored
        # alongside the first one.
        snap2 =deepcopy(SNAP_DATA)
        snap2['value'] = 17
        hash2 = self.m.add_metric_snap(snap2)

        assert_equals(len(hash), 32)
        assert_equals(self.m.metric_snaps[hash2], snap2)
        assert_equals(len(self.m.metric_snaps), 2) # two metricSnaps in there now.
        assert_equals(self.m.latest_snap["value"], snap2["value"])

        # now a third snap with the same value; shouldn't get stored.
        snap3 =deepcopy(SNAP_DATA)
        snap3['value'] = 17 #same as snap2 
        hash3 = self.m.add_metric_snap(snap2)

        assert_equals(hash3, hash2)
        assert_equals(len(self.m.metric_snaps), 2) # still just two metricSnaps in there.
        assert_equals(self.m.latest_snap["value"], snap2["value"])

    def test_as_dict(self):
        assert_equals(METRICS_DATA, self.m.__dict__) 

        # has to also work when there are snaps in the metric_snaps attr.
        snap = deepcopy(SNAP_DATA)
        hash = self.m.add_metric_snap(snap)
        print self.m.__dict__['metric_snaps'][hash]
        assert_equals(len(self.m.__dict__['metric_snaps']), 1)
        assert_equals(self.m.__dict__['metric_snaps'][hash], snap)
        assert_equals(self.m.__dict__['latest_snap'], snap)





class TestBiblio(unittest.TestCase):
    pass

class TestAliases(unittest.TestCase):

    def setUp(self):
        self.providers = api.providers
        pass
        
    def tearDown(self):
        pass 

    def test_init(self):
        a = models.Aliases()
        
        assert_equals(len(a.tiid), 36)
        
        a = models.Aliases("123456")
        assert_equals(a.tiid, "123456")

        a = models.Aliases(seed=ALIAS_DATA)
        assert a.tiid == "0987654321"
        assert a.title == ["Why Most Published Research Findings Are False"]

      
    def test_add(self):
        a = models.Aliases()
        a.add_alias("foo", "id1")
        a.add_alias("foo", "id2")
        a.add_alias("bar", "id1")

        assert a.last_modified < time.time()
        
        # check the data structure is correct
        expected = {"tiid": a.tiid, "foo":["id1", "id2"], "bar":["id1"]}
        del a.last_modified
        assert a.__dict__ == expected, a

    def test_add_unique(self):
        a = models.Aliases()
        a.add_alias("foo", "id1")
        a.add_alias("foo", "id2")
        a.add_alias("bar", "id1")

        to_add = [
            ("baz", "id1"),
            ("baz", "id2"),
            ("foo", "id3"),
            ("bar", "id1")
        ]
        a.add_unique(to_add)
        
        # check the data structure is correct
        expected = {"tiid": a.tiid,
                    "foo":["id1", "id2", "id3"], 
                    "bar":["id1"], 
                    "baz" : ["id1", "id2"]}
        del a.last_modified
        assert_equals(a.__dict__, expected)

        
    def test_add_potential_errors(self):
        # checking for the string/list type bug
        a = models.Aliases()
        a.doi = ["error"]
        a.add_alias("doi", "noterror")
        assert_equals(a.doi, ["error", "noterror"])
        
    def test_single_namespaces(self):
        a = models.Aliases(seed=ALIAS_DATA)
        
        assert a.doi == ["10.1371/journal.pmed.0020124"]
        assert a.url == ["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"]

        assert_equals(len(a.get_aliases_list()), 4)
        
        aliases = a.get_aliases_list("doi")
        assert aliases == [("doi", "10.1371/journal.pmed.0020124")], aliases
        
        aliases = a.get_aliases_list("title")
        assert aliases == [("title", "Why Most Published Research Findings Are False")]

    @raises(AttributeError)
    def test_missing(self):
        a = models.Aliases(seed=ALIAS_DATA)
        
        failres = a.my_missing_namespace
        assert failres == [], failres
        
    def test_multi_namespaces(self):
        a = models.Aliases(seed=ALIAS_DATA)
        
        ids = a.get_aliases_list(["doi", "url"])
        assert ids == [("doi", "10.1371/journal.pmed.0020124"),
                        ("url", "http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124")], ids
    
    def test_dict(self):
        a = models.Aliases(seed=ALIAS_DATA)
        assert a.as_dict() == ALIAS_DATA
        '''
    
    def test_DATA_validation(self):
        # FIXME: seed validation has not yet been implemented.  What does it
        # do, and how should it be tested?
        pass
    '''


    

        
        
        
