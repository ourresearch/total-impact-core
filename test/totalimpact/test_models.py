from totalimpact import models
from totalimpact.config import Configuration
from nose.tools import raises

class test_aliases:
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

        assert self.a.data == {"foo": ["id1", "id2"], \
            "bar":["id1"]}, self.a.data

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
        expected = {"foo":["id1", "id2"], "bar":["id1"]}
        assert res == expected, res
        
    

class Test_Metrics:
    def setup(self):
        self.m = models.Metrics()
        
    def test1(self):
        '''on validation check, throws error if missing key properties'''
        self.m.id = "Mendeley:readers"
        assert self.m.is_complete() == False