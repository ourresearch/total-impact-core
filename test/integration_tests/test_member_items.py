import os, unittest, time, json
from nose.tools import nottest, assert_equals

from totalimpact import dao, api
from totalimpact.config import Configuration


GITHUB_TEST_ORG = "bioperl"

class TestMemberItems(unittest.TestCase):
    
    def setUp(self):
        #setup api test client
        self.app = api.app
        self.app.testing = True
        self.client = self.app.test_client()
        
        # setup the database
        # member items doesn't need the database, but it is going to be started by the app anyway so make sure is test
        self.testing_db_name = "memberitems_test"
        self.old_db_name = self.app.config["DB_NAME"]
        self.app.config["DB_NAME"] = self.testing_db_name
        self.config = Configuration()
        self.d = dao.Dao(self.config)

    def tearDown(self):
        self.app.config["DB_NAME"] = self.old_db_name

        
    def tearDown(self):
        pass
        
    def test_member_items(self):

        # Test github org member_items
        response = self.client.get('/provider/github/memberitems?query=' + GITHUB_TEST_ORG + '&type=github_org')
        resp_list = json.loads(response.data)
        assert len(resp_list) > 12, len(resp_list)

        # comes back looking like this
        """
        [
            [
                "github", 
                [
                    "bioperl", 
                    "xml-html"
                ]
            ], 
            [
                "github", 
                [
                    "bioperl", 
                    "bioperl-papers"
                ]
            ], 
            [
                "github", 
                [
                    "bioperl", 
                    "bioperl-pise"
                ]
        ...
        """
        provider = [entry[0] for entry in resp_list]
        assert_equals(set(provider), set(["github"]))

        orgs = [entry[1][0] for entry in resp_list]
        assert_equals(set(orgs), set([GITHUB_TEST_ORG]))

        projects = [entry[1][1] for entry in resp_list]
        assert "bioperl-cookbook" in projects

        
