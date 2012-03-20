from totalimpact import models
from totalimpact.config import Configuration
from nose.tools import raises
import os, unittest, json, time

ALIAS_SEED = json.loads("""{
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
}""")

METRIC_SEED = json.loads("""{
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

class TestModels(unittest.TestCase):

    def test_01_aliases_init(self):
        a = models.Aliases()
        
        # a blank init always sets an id
        assert len(a.data.keys()) == 1
        assert a.data['tiid'] is not None
        assert a.tiid is not None
        assert a.tiid == a.data['tiid']
        
        a = models.Aliases("123456")
        
        # check our id has propagated
        assert len(a.data.keys()) == 1
        assert a.data['tiid'] == "123456"
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
        
    def test_02_aliases_add(self):
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
        
    def test_03_aliases_single_namespaces(self):
        a = models.Aliases(seed=ALIAS_SEED)
        
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
        
    def test_04_aliases_missing(self):
        a = models.Aliases(seed=ALIAS_SEED)
        
        failres = a.get_ids_by_namespace("my_missing_namespace")
        assert failres == [], failres
        
        failres = a.get_aliases_list("another_missing_namespace")
        assert failres == [], failres
        
    def test_05_aliases_multi_namespaces(self):
        a = models.Aliases(seed=ALIAS_SEED)
        
        ids = a.get_aliases_list(["doi", "url"])
        assert ids == [("doi", "10.1371/journal.pmed.0020124"),
                        ("url", "http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124")], ids
    
    def test_06_aliases_dict(self):
        a = models.Aliases(seed=ALIAS_SEED)
        assert a.get_aliases_dict() == ALIAS_SEED
    
    def test_07_alias_seed_validation(self):
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
    
    def test_08_provider_metric_init(self):
        m = models.ProviderMetric(seed=METRIC_SEED)
        
        assert m.id == "Mendeley:readers"
        assert m.value() == 16
        assert m.created == 1233442897.234
        assert m.last_modified == 1328569492.406
        assert m.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        assert m.meta() == METRIC_SEED['meta']
        
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
                                    meta=METRIC_SEED['meta'])
        assert m.meta() == METRIC_SEED['meta']
    
    def test_09_provider_metric_get_set(self):
        m = models.ProviderMetric(seed=METRIC_SEED)
        stale = time.time()
        
        assert m.value() == 16
        m.value(17)
        assert m.value() == 17
        assert m.last_modified > stale
        stale = m.last_modified
        
        assert m.meta() == METRIC_SEED['meta']
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
        
    
    
""" NOTE: incoroprated into above tests; leaving for reference for the time being
class Test_Aliases:
    def setup(self):
        self.a = models.Aliases()
        self.a.add_alias("foo", "id1")
        self.a.add_alias("foo", "id2")
        self.a.add_alias("bar", "id1") 

    def teardown(self):
        pass

    def test1(self):
        ''' alias gives self a tiid at creation'''

        assert len(self.a.tiid) == 36, "len was " + str(len(self.a.tiid))

    def test2(self):
        '''adds new aliases to the  object'''

        expected = {"tiid":self.a.tiid, "foo":["id1", "id2"], "bar":["id1"]}
        assert self.a.data == expected, self.a.data

    def test3(self):
        '''gets an alias based on its namespace'''

        res = self.a.get_ids_by_namespace("foo")
        assert res == ["id1", "id2"], res

        failres = self.a.get_ids_by_namespace("my_missing_namespace")
        assert failres == [], failres

    def test4(self):
        '''gets a list of aliases from a list of namespaces'''
        
        res = self.a.get_aliases_list(["foo", "bar"])
        expected = [("foo", "id1"), ("foo", "id2"), ("bar", "id1")]
        assert res == expected, res

        res = self.a.get_aliases_list(["foo"])
        expected = [("foo", "id1"), ("foo", "id2")]
        assert res == expected, res
    
    def test5(self):
        '''get aliases as a dictionary'''
        res = self.a.get_aliases_dict()
        expected = {"tiid":self.a.tiid, "foo":["id1", "id2"], "bar":["id1"]}
        assert res == expected, res
"""

class Test_Metrics:
    def setup(self):
        self.m = models.Metrics()
        
    def not_implemented_yet(self):
        '''on validation check, throws error if missing key properties'''
       
        config = Configuration(os.getcwd() + '/test/complete_metric.json', False)
        
        self.m.properties = config.cfg
        #assert self.m.is_complete == True
        
        del self.m.properties['value']
        #assert self.m.is_complete == False