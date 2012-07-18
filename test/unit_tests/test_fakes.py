import unittest, re
from test.utils import slow, http
from nose.tools import assert_equals, raises
from totalimpact.fakes import IdSampler


class TestDoiSampler(unittest.TestCase):
    
    doi_regex = "10\.\d+" # just tests the front part, won't match whole string 

    def test_get_doi(self):
        sampler = IdSampler()
        dois_list = sampler.get_dois()
        assert re.match(self.doi_regex, dois_list[0]), dois_list
        
    def test_get_multiple_dois(self):
        sampler = IdSampler()
        dois_list = sampler.get_dois(10)
        assert_equals(len(dois_list), 10)
        assert re.match(self.doi_regex, dois_list[7]), dois_list
        
        
class TestGitHubUserNameSampler(unittest.TestCase):
    
    def test_get_github_username(self):
        sampler = IdSampler()
        username = sampler.get_github_username()
        assert isinstance(username, basestring)
        assert len(username) > 0, username
