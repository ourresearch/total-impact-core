from totalimpact import models
from totalimpact.config import Configuration
from nose.tools import raises, assert_equals
import os, unittest, json, time
from copy import deepcopy

ALIAS_SEED = json.loads("""{
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
}""")

ALIAS_SEED_CANONICAL = json.loads("""{
    "TIID":"0987654321",
    "TITLE":["Why Most Published Research Findings Are False"],
    "URL":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "DOI": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
}""")

PM_SEED = json.loads("""{
    "id": "Mendeley:readers",
    "value": 16,
    "created": 1233442897.234,
    "last_modified": 1328569492.406,
    "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
    "meta": {
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
""")
PM_SEED_HASH = "d8c8f25061da78cc905e9b837d1c78ed"

METRICS_SEED = json.loads("""
{
    "meta": {
        "Mendeley": {
            "last_modified": 128798498.234,
            "last_requested": 2139841098.234,
            "ignore": false
        }
    },
    "bucket":{}
}
""")
METRICS_SEED['bucket'][PM_SEED_HASH] = PM_SEED

BIBLIO_SEED = json.loads("""
    {
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
""")

ITEM_SEED = json.loads("""
{
    "created": 23112412414.234,
    "last_modified": 12414214.234,
    "last_requested": 124141245.234
}
""")
ITEM_SEED["aliases"] = ALIAS_SEED
ITEM_SEED["metrics"] = METRICS_SEED
ITEM_SEED["biblio"] = BIBLIO_SEED

class TestItem():

    def setUp(self):

        class _MockDao():
            def get(self, id):
                return ITEM_SEED

        self.d = _MockDao()

    def test_new_testing_class(self):
        assert True

    def test_mock_dao(self):
        assert_equals(self.d.get("123"), ITEM_SEED)

    def test_item_init(self):
        i = models.Item(self.d)
        assert_equals(len(i.id), 32) # made a uuid, yay

    def test_load(self):
        i = models.Item(self.d, id="123")
        i.load()
        assert_equals(i.aliases, ITEM_SEED["aliases"])
        assert_equals(i.created, ITEM_SEED["created"])
        assert i.last_requested > ITEM_SEED["last_requested"]

    @raises(LookupError)
    def test_load_with_nonexistant_item_fails(self):
        i = models.Item(self.d, id="123")
        self.d.get = lambda id: None # that item doesn't exist in the db
        i.load()
        


        '''
        
        i = models.Item("12345", aliases=deepcopy(ALIAS_SEED), metrics=deepcopy(METRICS_SEED), biblio=deepcopy(BIBLIO_SEED))
        assert isinstance(i.aliases, models.Aliases)
        assert isinstance(i.metrics, models.Metrics)
        assert isinstance(i.biblio, models.Biblio)

        assert i.aliases.data == ALIAS_SEED_CANONICAL, i.aliases.data
        # can only compare the buckets, as the meta objects change when they are added
        assert i.metrics.data['bucket'] == METRICS_SEED['bucket'], (i.metrics.data, METRICS_SEED)
        assert i.biblio.data == BIBLIO_SEED
        
        a = models.Aliases(seed=deepcopy(ALIAS_SEED))
        m = models.Metrics(seed=deepcopy(METRICS_SEED))
        b = models.Biblio(seed=deepcopy(BIBLIO_SEED))
        
        i = models.Item("12345", aliases=a, metrics=m, biblio=b)
        assert i.aliases.data == ALIAS_SEED_CANONICAL
        # can only compare the buckets, as the meta objects change when they are added
        assert i.metrics.data['bucket'] == METRICS_SEED['bucket'], (i.metrics.data, METRICS_SEED)
        assert i.biblio.data == BIBLIO_SEED
        
        i = models.Item(id="12345", seed=deepcopy(ITEM_SEED))
        assert i.aliases.data == ALIAS_SEED_CANONICAL
        assert i.metrics.data['bucket'] == METRICS_SEED['bucket'], (i.metrics.data, METRICS_SEED)
        assert i.biblio.data == BIBLIO_SEED
        '''

class TestModels(unittest.TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_01_aliases_init(self):
        a = models.Aliases()
        
        # a blank init always sets an id
        assert len(a.data.keys()) == 1
        assert a.data[models.Aliases.NS.TIID] is not None
        assert a.tiid is not None
        assert a.tiid == a.data[models.Aliases.NS.TIID]
        
        a = models.Aliases("123456")
        
        # check our id has propagated
        assert len(a.data.keys()) == 1
        assert a.data[models.Aliases.NS.TIID] == "123456"
        assert a.tiid == "123456"
        
        a = models.Aliases(seed=ALIAS_SEED)
        
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
    
    def test_02_aliases_canonical(self):
        a = models.Aliases()
        
        assert a._synonym("DIGITAL OBJECT IDENTIFIER") == a.NS.DOI
        assert a._synonym("MADE UP NAMESPACE") == "MADE UP NAMESPACE"
        assert a._synonym("URL") == a.NS.URL
        
        assert a.canonicalise("doi") == a.NS.DOI
        assert a.canonicalise("iri") == a.NS.IRI
        assert a.canonicalise("digital object identifier") == a.NS.DOI
        assert a.canonicalise("made up namespace") == "MADE UP NAMESPACE"
        
        assert a.canonical_dict(ALIAS_SEED) == ALIAS_SEED_CANONICAL, a.canonical_dict(ALIAS_SEED)
    
    def test_03_aliases_add(self):
        a = models.Aliases()
        a.add_alias("foo", "id1")
        a.add_alias("foo", "id2")
        a.add_alias("bar", "id1")
        
        # check the data structure is correct
        expected = {"TIID": a.tiid, "FOO":["id1", "id2"], "BAR":["id1"]}
        assert a.data == expected, a.data
        
        to_add = [
            ("baz", "id1"),
            ("baz", "id2"),
            ("foo", "id3"),
            ("bar", "id1")
        ]
        a.add_unique(to_add)
        
        # check the data structure is correct
        expected = {"TIID": a.tiid, 
                    "FOO":["id1", "id2", "id3"], 
                    "BAR":["id1"], 
                    "BAZ" : ["id1", "id2"]}
        assert a.data == expected, a.data
        
    def test_04_aliases_single_namespaces(self):
        a = models.Aliases(seed=ALIAS_SEED)
        
        ids = a.get_ids_by_namespace("doi")
        assert ids == ["10.1371/journal.pmed.0020124"]
        
        ids = a.get_ids_by_namespace("url")
        assert ids == ["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"]
        
        aliases = a.get_aliases_list()
        assert len(aliases) == 4
        
        aliases = a.get_aliases_list("doi")
        assert aliases == [("DOI", "10.1371/journal.pmed.0020124")], aliases
        
        aliases = a.get_aliases_list("title")
        assert aliases == [("TITLE", "Why Most Published Research Findings Are False")]
        
    def test_05_aliases_missing(self):
        a = models.Aliases(seed=ALIAS_SEED)
        
        failres = a.get_ids_by_namespace("my_missing_namespace")
        assert failres == [], failres
        
        failres = a.get_aliases_list("another_missing_namespace")
        assert failres == [], failres
        
    def test_06_aliases_multi_namespaces(self):
        a = models.Aliases(seed=ALIAS_SEED)
        
        ids = a.get_aliases_list(["doi", "url"])
        assert ids == [("DOI", "10.1371/journal.pmed.0020124"),
                        ("URL", "http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124")], ids
    
    def test_07_aliases_dict(self):
        a = models.Aliases(seed=ALIAS_SEED)
        assert a.get_aliases_dict() == ALIAS_SEED_CANONICAL
    
    def test_08_alias_seed_validation(self):
        # FIXME: seed validation has not yet been implemented.  What does it
        # do, and how should it be tested?
        pass
    
    """{
        "id": "Mendeley:readers",
        "value": 16,
        "created": 1233442897.234,
        "last_modified": 1328569492.406,
        "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
        "meta": {
            "display_name": "readers"
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "Mendeley readers: the number of readers of the article",
            "icon": "http://www.mendeley.com/favicon.ico",
            "category": "bookmark",
            "can_use_commercially": "0",
            "can_embed": "1",
            "can_aggregate": "1",
            "other_terms_of_use": "Must show logo and say 'Powered by Santa'",
        }
    }
    """
    
    def test_09_provider_metric_init(self):
        m = models.ProviderMetric(seed=deepcopy(PM_SEED))
        
        assert m.id == "Mendeley:readers"
        assert m.value() == 16
        assert m.created == 1233442897.234
        assert m.last_modified == 1328569492.406
        assert m.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        assert m.meta() == PM_SEED['meta']
        assert m.data == PM_SEED
        
        now = time.time()
        m = models.ProviderMetric(id="Richard:metric", 
                                    value=23, created=now, last_modified=now,
                                    provenance_url="http://total-impact.org/")
        assert m.id == "Richard:metric"
        assert m.value() == 23
        assert m.created == now
        assert m.last_modified == now
        assert m.provenance() == ["http://total-impact.org/"]
        assert len(m.meta()) == 0
        
        m = models.ProviderMetric(id="Richard:metric", 
                                    value=23, created=now, last_modified=now,
                                    provenance_url="http://total-impact.org/",
                                    meta=PM_SEED['meta'])
        assert m.meta() == PM_SEED['meta']
    
    def test_10_provider_metric_get_set(self):
        m = models.ProviderMetric(seed=deepcopy(PM_SEED))
        stale = time.time()
        
        assert m.value() == 16
        m.value(17)
        assert m.value() == 17
        assert m.last_modified > stale
        stale = m.last_modified
        
        assert m.meta() == PM_SEED['meta']
        m.meta({"test": "meta"})
        assert m.meta() == {"test" : "meta"}
        assert m.last_modified > stale
        stale = m.last_modified
        
        assert m.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        m.provenance("http://total-impact.org")
        assert m.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/", "http://total-impact.org"]
        assert m.last_modified > stale
        
        m.provenance(["http://total-impact.org"])
        assert m.provenance() == ["http://total-impact.org"], m.provenance()
    
    """
    {
        "meta": {
            "PROVIDER_ID": {
                "last_modified": 128798498.234,
                "last_requested": 2139841098.234,
                "ignore": false
            }
        },
        "bucket":[
            "LIST OF PROVIDER METRIC OBJECTS"
        ]
    }
    """
    
    def test_11_metrics_init(self):
        m = models.Metrics()
        
        assert len(m.meta()) == 4, m.meta()
        assert len(m.list_provider_metrics()) == 0
        
        m = models.Metrics(deepcopy(METRICS_SEED))
        
        assert len(m.meta()) == 5, m.meta()
        assert len(m.list_provider_metrics()) == 1
        
        assert m.meta()['Mendeley'] is not None
        assert m.meta()['Mendeley']['last_modified'] == 128798498.234
        assert m.meta()['Mendeley']['last_requested'] != 0  # don't know exactly what it will be
        assert not m.meta()['Mendeley']['ignore']
        
        assert m.meta()['Wikipedia'] is not None
        assert m.meta()['Wikipedia']['last_modified'] == 0
        assert m.meta()['Wikipedia']['last_requested'] != 0 # don't know exactly what it will be
        assert not m.meta()['Wikipedia']['ignore']
        
        pm = m.list_provider_metrics()[0]
        assert pm == models.ProviderMetric(seed=deepcopy(PM_SEED)), (pm.data, PM_SEED)
        
    def test_12_metrics_meta(self):
        m = models.Metrics(METRICS_SEED)
        assert len(m.meta()) == 5, m.meta()
        assert m.meta()['Mendeley'] is not None
        
        assert m.meta("Mendeley") is not None
        assert m.meta("Mendeley") == m.meta()['Mendeley']
    
    def test_13_metrics_add_provider_metric(self):
        now = time.time()
        
        m = models.Metrics(deepcopy(METRICS_SEED))
        new_seed = deepcopy(PM_SEED)
        new_seed['value'] = 25
        m.add_provider_metric(models.ProviderMetric(seed=new_seed))
        
        assert len(m.meta()) == 5, m.meta()
        assert len(m.list_provider_metrics()) == 2
        assert len(m.list_provider_metrics(new_seed['id'])) == 2
        
        assert m.meta('Mendeley')['last_modified'] > now
        
    def test_14_metrics_list_provider_metrics(self):
        m = models.Metrics(deepcopy(METRICS_SEED))
        
        assert len(m.list_provider_metrics()) == 1
        assert m.list_provider_metrics("Mendeley:readers")[0] == models.ProviderMetric(seed=deepcopy(PM_SEED))
        
        assert len(m.list_provider_metrics("Some:other")) == 0
    
    def test_15_metrics_canonical(self):
        m = models.Metrics()
        
        simple_dict = {"one" : 1, "two" : 2, "three" : 3}
        simple_expected = "one1three3two2"
        canon = m._canonical_repr(simple_dict)
        assert canon == simple_expected, (canon, simple_expected)
        
        nested_dict = { "one" : 1, "two" : { "three" : 3, "four" : 4 } }
        nested_expected = "one1two{four4three3}"
        canon = m._canonical_repr(nested_dict)
        assert canon == nested_expected, (canon, nested_expected)
        
        nested_list = {"one" : 1, "two" : ['c', 'b', 'a']}
        list_expected = "one1two[abc]"
        canon = m._canonical_repr(nested_list)
        assert canon == list_expected, (canon, list_expected)
        
        nested_both = {"zero" : 0, "one" : {"two" : 2, "three" : 3}, "four" : [7,6,5]}
        both_expected = "four[567]one{three3two2}zero0"
        canon = m._canonical_repr(nested_both)
        assert canon == both_expected, (canon, both_expected)
        
    def test_15_metrics_hash(self):
        m = models.Metrics()
        pm = models.ProviderMetric(seed=deepcopy(PM_SEED))
        
        hash = m._hash(pm)
        assert hash == PM_SEED_HASH, (hash, PM_SEED_HASH)
        
        m.add_provider_metric(pm)
        assert m.data['bucket'].keys()[0] == PM_SEED_HASH
    
    # FIXME: Biblio has not been fully explored yet, so no tests for it
    
    """
    {
        "aliases": alias_object, 
        "metrics": metric_object, 
        "biblio": biblio_object,
        "created": 23112412414.234,
        "last_modified": 12414214.234,
        "last_requested": 124141245.234
    }
    """
    

        
        
        