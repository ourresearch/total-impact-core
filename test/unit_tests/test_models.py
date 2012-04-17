from nose.tools import raises, assert_equals, nottest
import os, unittest, json, time, yaml
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
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
    }

ALIAS_CANONICAL_DATA = {
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
    "ignore": False,
    "metric_snaps": {
        "thisissupposedtobeahash": SNAP_DATA
    },
    "latest_snap": SNAP_DATA
}

METRICS_DATA2 = {
    "ignore": False,
    "metric_snaps": {},
    "latest_snap": None
}

METRICS_DATA3 = {
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
    "metrics": { # this could be a list, but limiting to dicts makes processing easier.
        "plos:html_views": METRICS_DATA,
        "plos:pdf_views": METRICS_DATA2
    },
    "biblio": BIBLIO_DATA
}
    
TEST_DB_NAME = "test_models"


class TestSaveable():
    def setUp(self):
        print ITEM_DATA
        pass

    def test_id_gets_set(self):
        s = models.Saveable(dao="dao")
        assert_equals(len(s.id), 32)

        s2 = models.Saveable(dao="dao", id="123")
        assert_equals(s2.id, "123")

    def test_as_dict(self):
        s = models.Saveable(dao="dao")
        s.foo = "a var"
        s.bar = "another var"
        assert_equals(s.as_dict()['foo'], "a var")

    def test_as_dict_recursive(self):
        s = models.Saveable(dao="dao")
        class TestObj:
            pass
        
        foo =  TestObj()
        foo.bar = "I'm in foo!"

        s.constituent_dict = {}
        s.constituent_dict["foo_obj"] = foo

        assert_equals(s.as_dict()['constituent_dict']['foo_obj']['bar'], foo.bar)

    def test__update_dict(self):
        '''These tests are more naturalistic because they use the objects
        we're using. but in future, toy objects are way easier to work with and
        grok later.'''

        item_response = deepcopy(ITEM_DATA)
        item_response2 = deepcopy(ITEM_DATA)

        dao = MockDao()
        dao.setResponses([item_response])

        # simulate pulling an item out of the db
        item = models.ItemFactory.make(dao, item_response['_id'])

        # note the item has an 'id' but not an '_id' attr
        assert_equals(item.id, item_response['_id'])
        assert_equals(item.aliases.__class__.__name__, "Aliases")

        # now let's simulate adding some stuff to this object
        # change a string
        now = "99999999999.9" # it's the future!
        item.last_modified = now

        # add a snap to an existing Metrics object
        new_snap = deepcopy(SNAP_DATA)
        new_snap['value'] = 22
        item.metrics["plos:html_views"].metric_snaps["a_new_snap"] = new_snap

        # add a whole 'nother Metrics object (a list item)
        item.metrics["test:a_new_metric"] = METRICS_DATA3

        # Meanwhile, it seems the item in the db has changed, thanks to other Providers:
        item_response2["metrics"]["test:while_you_were_away"] = METRICS_DATA3
        new_snap = deepcopy(SNAP_DATA)
        new_snap['value'] = 44 
        item_response2["metrics"]["plos:html_views"]["metric_snaps"] \
            ["while_you_were_away_snap"] = new_snap

        # now let's see if this works:
        output = item._update_dict(item_response2)
        print yaml.dump(output)

        # things that are common to both dicts are preserved
        assert_equals(output["aliases"], item_response2["aliases"])

        # when strings differ, the object's version takes priority
        assert_equals(output["last_modified"], now)

        # plos:html_views should have one snap initially, +1 we added right
        # away, + 1 back from the database = 3
        assert_equals(len(output["metrics"]["plos:html_views"]["metric_snaps"]), 3)

        # locally and remotely added metrics are preserved
        assert_equals(output["metrics"]["test:a_new_metric"]["ignore"], False)
        assert_equals(output["metrics"]["test:while_you_were_away"]["ignore"], False)

        # locally and remotely added metric snaps are preserved
        assert_equals(output["metrics"]["plos:html_views"]["metric_snaps"] \
            ["while_you_were_away_snap"]["value"], 44)
        assert_equals(output["metrics"]["test:while_you_were_away"]["ignore"], False)

        def save(self):
            # not much to test here, unless we want to use the real dao.
            pass



class TestItemFactory():

    def setUp(self):
        self.d = MockDao()

    def test_make_new(self):
        '''create an item from scratch.'''
        item = models.ItemFactory.make(self.d)
        assert_equals(len(item.id), 32)
        assert item.created < time.time

    def test_make_from_db(self):
        self.d.setResponses([deepcopy(ITEM_DATA)])

        item = models.ItemFactory.make(self.d, "123")
        
        assert_equals(item.id, ITEM_DATA['_id'])
        assert_equals(item.aliases.__class__.__name__, "Aliases")
        assert_equals(item.as_dict()["aliases"], ITEM_DATA["aliases"])

    @raises(LookupError)
    def test_load_with_nonexistant_item_fails(self):
        self.d.setResponses([None])
        item = models.ItemFactory.make(self.d, "123")

class TestItem():

    def setUp(self):
        self.d = MockDao()
        self.d.setResponses([deepcopy(ITEM_DATA)])


    def test_mock_dao(self):
        assert_equals(self.d.get("123"), ITEM_DATA)

    def ITEM_DATA_init(self):
        i = models.Item(self.d)
        assert_equals(len(i.id), 32) # made a uuid, yay

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

class TestCollectionFactory():

    def setUp(self):        
        self.d = MockDao()
        
    def COLLECTION_DATA_load(self):
        self.d.get = lambda id: deepcopy(COLLECTION_DATA)
        c = models.Collection(self.d, id="SomeCollectionId")
        c.load()
        assert_equals(c.collection_name, "My Collection")
        assert_equals(c.item_ids(), [u'origtiid1', u'origtiid2'])

    @raises(LookupError)
    def test_load_with_nonexistant_collection_fails(self):
        self.d.setResponses([None])
        factory = models.CollectionFactory.make(self.d, "AnUnknownCollectionId")

class TestCollection():

    def setUp(self):        
        self.d = MockDao()

    def test_mock_dao(self):
        self.d.setResponses([ deepcopy(COLLECTION_DATA)])
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

    def test_collection_delete(self):
        self.d.delete = lambda id: True
        c = models.Collection(self.d, id="SomeCollectionId")
        response = c.delete()
        assert_equals(response, True)


class TestMetricSnap(unittest.TestCase):
    pass

class TestMetrics(unittest.TestCase):


    def setUp(self):
        self.m = models.Metrics()

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
        assert_equals(METRICS_DATA["ignore"], self.m.__dict__["ignore"])

        # has to also work when there are snaps in the metric_snaps attr.
        snap = deepcopy(SNAP_DATA)
        hash = self.m.add_metric_snap(snap)
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
        a = models.Aliases()

        a = models.Aliases(seed=ALIAS_DATA)
        assert a.title == ["Why Most Published Research Findings Are False"]

      
    def test_add(self):
        a = models.Aliases()
        a.add_alias("foo", "id1")
        a.add_alias("foo", "id2")
        a.add_alias("bar", "id1")

        assert a.last_modified < time.time()
        
        # check the data structure is correct
        expected = {"foo":["id1", "id2"], "bar":["id1"]}
        del a.last_modified, a.created
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
        expected = {"foo":["id1", "id2", "id3"], 
                    "bar":["id1"], 
                    "baz" : ["id1", "id2"]}
        del a.last_modified, a.created
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

        assert_equals(len(a.get_aliases_list()), 3)
        
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




    

        
        
        
