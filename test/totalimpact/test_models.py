from totalimpact import models

def setup_module():
    pass

def teardown_module():
    pass

def test1():
    ''' alias gives self a tiid at creation'''
    a = models.aliases()
    assert len(a.tiid) == 36, "len was " + str(len(a.tiid))
    
def test2():
    '''adds new aliases to the  object'''
    a = models.aliases()
    
    a.add_alias("my_namespace", "my_id")
    assert a.data == {"my_namespace": ["my_id"]}, a.data
    
    a.add_alias("my_namespace", "my_2nd_id")
    assert a.data == {"my_namespace": ["my_id", "my_2nd_id"]}, a.data
    
    a.add_alias("my_2nd_namespace", "my_id")
    assert a.data == {"my_namespace": ["my_id", "my_2nd_id"], \
        "my_2nd_namespace":["my_id"]}, a.data
        
def test3():
    '''gets an alias based on its namespace'''
    a = models.aliases()
    a.add_alias("my_namespace", "my_id")
    a.add_alias("my_namespace", "my_2nd_id")
    
    res = a.get_ids("my_namespace")
    assert res == ["my_id", "my_2nd_id"], res
    
    failres = a.get_ids("my_missing_namespace")
    assert failres == [], failres
    