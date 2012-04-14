from nose.tools import raises, assert_equals, nottest
import os, unittest, json, time
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

METRIC_NAME = "views"
METRICS_DATA = {
    "name": METRIC_NAME,
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
    "created": 1330260456.916,
    "last_modified": 12414214.234,
    "last_requested": 124141245.234, 
    "aliases": ALIAS_DATA,
    "metrics": METRICS_DATA,
    "biblio": BIBLIO_DATA
    }
    
TEST_DB_NAME = "test_models"

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
        i = models.Item(self.d, id="123")
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
    def test_init(self):
        snap_simple = models.MetricSnap(seed=deepcopy(SNAP_DATA))

        assert snap_simple.id == "mendeley:readers"
        assert snap_simple.value() == 16
        assert snap_simple.created == 1233442897.234
        assert snap_simple.last_modified == 1328569492.406
        assert snap_simple.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        assert snap_simple.static_meta() == SNAP_DATA['static_meta']
        assert snap_simple.data == SNAP_DATA

        now = time.time()
        snap = models.MetricSnap(id="richard:metric",
                                    value=23, created=now, last_modified=now,
                                    provenance_url="http://total-impact.org/")
        assert snap.id == "richard:metric"
        assert snap.value() == 23
        assert snap.created == now
        assert snap.last_modified == now
        assert snap.provenance() == ["http://total-impact.org/"]
        assert len(snap.static_meta()) == 0

        snap_from_DATA = models.MetricSnap(id="richard:metric",
                                    value=23, created=now, last_modified=now,
                                    provenance_url="http://total-impact.org/",
                                    static_meta=SNAP_DATA['static_meta'])
        assert snap_from_DATA.static_meta() == SNAP_DATA['static_meta']

    def test_get_set(self):
        snap = models.MetricSnap(seed=deepcopy(SNAP_DATA))
        stale = time.time()

        assert snap.value() == 16
        snap.value(17)
        assert snap.value() == 17
        assert snap.last_modified > stale
        stale = snap.last_modified

        assert snap.static_meta() == SNAP_DATA['static_meta']
        snap.static_meta({"test": "static_meta"})
        assert snap.static_meta() == {"test" : "static_meta"}
        assert snap.last_modified > stale
        stale = snap.last_modified

        assert snap.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        snap.provenance("http://total-impact.org")
        assert snap.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/", "http://total-impact.org"]
        assert snap.last_modified > stale

        snap.provenance(["http://total-impact.org"])
        assert snap.provenance() == ["http://total-impact.org"], snap.provenance()

class TestMetrics(unittest.TestCase):


    def setUp(self):
        self.m = models.Metrics(METRIC_NAME)

    def test_init(self):
        assert len(self.m.metric_snaps) == 0
        assert_equals(self.m.name, METRIC_NAME )

    def test_add_metric_snap(self):
        start_time = time.time()

        snap1 = models.MetricSnap(seed=deepcopy(SNAP_DATA))
        hash = self.m.add_metric_snap(snap1)

        assert_equals(len(hash), 32)
        assert_equals(self.m.metric_snaps[hash], snap1)
        assert_equals(len(self.m.metric_snaps), 1)
        assert_equals(self.m.latest_snap.data["value"], snap1.data["value"])

        # the we've changed something, so the last_modified value should change
        assert  self.m.last_modified > start_time

        # let's try adding a new snap; this has a new value, so it'll get stored
        # alongside the first one.
        snap2 = models.MetricSnap(seed=deepcopy(SNAP_DATA))
        snap2.data['value'] = 17
        hash2 = self.m.add_metric_snap(snap2)

        assert_equals(len(hash), 32)
        assert_equals(self.m.metric_snaps[hash2], snap2)
        assert_equals(len(self.m.metric_snaps), 2) # two metricSnaps in there now.
        assert_equals(self.m.latest_snap.data["value"], snap2.data["value"])

        # now a third snap with the same value; shouldn't get stored.
        snap3 = models.MetricSnap(seed=deepcopy(SNAP_DATA))
        snap3.data['value'] = 17 #same as snap2
        hash3 = self.m.add_metric_snap(snap2)

        assert_equals(hash3, hash2)
        assert_equals(len(self.m.metric_snaps), 2) # still just two metricSnaps in there.
        assert_equals(self.m.latest_snap.data["value"], snap2.data["value"])

    def test_as_dict(self):
        assert_equals(METRICS_DATA, self.m.__dict__)

        # has to also work when there are snaps in the metric_snaps attr.
        snap_data = deepcopy(SNAP_DATA)
        snap = models.MetricSnap(snap_data)
        hash = self.m.add_metric_snap(snap)
        print self.m.__dict__['metric_snaps'][hash]
        assert_equals(self.m.__dict__['metric_snaps'][hash], snap)



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
        
        # a blank init always sets an id
        assert len(a.data.keys()) == 1
        assert a.data["tiid"] is not None
        assert a.tiid is not None
        assert a.tiid == a.data["tiid"]
        
        a = models.Aliases("123456")
        
        # check our id has propagated
        assert len(a.data.keys()) == 1
        assert a.data["tiid"] == "123456"
        assert a.tiid == "123456"
        
        a = models.Aliases(seed=ALIAS_DATA)
        
        assert len(a.data.keys()) == 6
        assert a.tiid == "0987654321"
        assert a.title == ["Why Most Published Research Findings Are False"]
        assert a.url == ["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"]
        assert a.doi == ["10.1371/journal.pmed.0020124"]
        assert a.created == 12387239847.234
        assert a.last_modified == 1328569492.406
        
        a = models.Aliases(tiid="abcd", doi="10.1371/journal/1", title=["First", "Second"])
        
        assert len(a.data.keys()) == 3
        assert a.tiid == "abcd"
        assert a.doi == ["10.1371/journal/1"]
        assert a.title == ["First", "Second"]
        
    def test_add(self):
        a = models.Aliases()
        a.add_alias("foo", "id1")
        a.add_alias("foo", "id2")
        a.add_alias("bar", "id1")
        
        # check the data structure is correct
        expected = {"tiid": a.tiid, "foo":["id1", "id2"], "bar":["id1"]}
        assert a.data == expected, a.data
        
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
        assert a.data == expected, a.data
        
    def test_add_potential_errors(self):
        # checking for the string/list type bug
        a = models.Aliases()
        a.data["doi"] = "error"
        a.add_alias("doi", "noterror")
        assert a.data['doi'] == ["error", "noterror"], a.data['doi']
        
    def test_single_namespaces(self):
        a = models.Aliases(seed=ALIAS_DATA)
        
        ids = a.get_ids_by_namespace("doi")
        assert ids == ["10.1371/journal.pmed.0020124"]
        
        ids = a.get_ids_by_namespace("url")
        assert ids == ["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"]
        
        aliases = a.get_aliases_list()
        assert len(aliases) == 4
        
        aliases = a.get_aliases_list("doi")
        assert aliases == [("doi", "10.1371/journal.pmed.0020124")], aliases
        
        aliases = a.get_aliases_list("title")
        assert aliases == [("title", "Why Most Published Research Findings Are False")]
        
    def test_missing(self):
        a = models.Aliases(seed=ALIAS_DATA)
        
        failres = a.get_ids_by_namespace("my_missing_namespace")
        assert failres == [], failres
        
        failres = a.get_aliases_list("another_missing_namespace")
        assert failres == [], failres
        
    def test_multi_namespaces(self):
        a = models.Aliases(seed=ALIAS_DATA)
        
        ids = a.get_aliases_list(["doi", "url"])
        assert ids == [("doi", "10.1371/journal.pmed.0020124"),
                        ("url", "http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124")], ids
    
    def test_dict(self):
        a = models.Aliases(seed=ALIAS_DATA)
        assert a.get_aliases_dict() == ALIAS_CANONICAL_DATA
    
    def test_DATA_validation(self):
        # FIXME: seed validation has not yet been implemented.  What does it
        # do, and how should it be tested?
        pass



    

        
        
        
