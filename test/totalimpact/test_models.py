from totalimpact import models

class test_aliases:
    def setup(self):
        self.a = models.aliases()
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
        
        res = self.a.get_aliases(["foo", "bar"])
        expected = [("foo", "id1"), ("foo", "id2"), ("bar", "id1")]
        assert res == expected, res

        res = self.a.get_aliases(["foo"])
        expected = [("foo", "id1"), ("foo", "id2")]
        assert res == expected, res
    