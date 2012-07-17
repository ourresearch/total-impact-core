import unittest, re
from test.utils import slow, http
from nose.tools import assert_equals, raises
from totalimpact.fakes import DoiSampler, GitHubUsernameSampler


class TestDoiSampler(unittest.TestCase):
    
    doi_regex = "10\.\d+" # just tests the front part, won't match whole string 

    def test_get_doi(self):
        sampler = DoiSampler()
        dois_list = sampler.get()
        assert re.match(self.doi_regex, dois_list[0]), dois_list
        
    def test_get_multiple_dois(self):
        sampler = DoiSampler()
        dois_list = sampler.get(10)
        assert_equals(len(dois_list), 10)
        assert re.match(self.doi_regex, dois_list[7]), dois_list
        
        
class TestGitHubUserNameSampler(unittest.TestCase):
    
    def test_get(self):
        sampler = GitHubUsernameSampler()
        username = sampler.get()
        assert len(username) > 0, username
