import nose, os
from totalimpact import dao

def setup():
    """
    sets up the nose fixture for all our tests. used to make sure that everyone
    is using the test database instead of "ti," which is used for functional tests.
    """
    os.environ["CLOUDANT_DB"] = "unit_tests"

def tearDown(self):
#    os.putenv("CLOUDANT_DB", "ti")
    pass
