from totalimpact import models
from totalimpact.config import Configuration
from nose.tools import raises
import os, unittest, json

ALIAS_SEED = json.loads("""{
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
}""")

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