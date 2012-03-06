from totalimpact import models

def setup_module():
    pass

def teardown_module():
    pass

def testModelsInstantiates():
    a = models.aliases()
    assert len(a.tiid) == 36, "len was " + str(len(a.tiid))
    