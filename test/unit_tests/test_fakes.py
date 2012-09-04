import unittest, re
from test.utils import slow, http
from nose.tools import assert_equals, raises
from totalimpact.fakes import IdSampler


class TestDoiSampler(unittest.TestCase):
    
    doi_regex = "10\.\d+" # just tests the front part, won't match whole string 

    @slow
    def test_get_doi(self):
        sampler = IdSampler()
        dois_list = sampler.get_dois()
        try:
            assert re.match(self.doi_regex, dois_list[0]), dois_list
        except IndexError:
            print "random doi is down"

    @slow
    def test_get_multiple_dois(self):
        sampler = IdSampler()
        dois_list = sampler.get_dois(10)
        try:
            dois_list[0]  # test to see if random doi service down first
            assert_equals(len(dois_list), 10)
            assert re.match(self.doi_regex, dois_list[7]), dois_list
        except IndexError:
            print "random doi is down"
        
        
class TestGitHubUserNameSampler(unittest.TestCase):

    @slow
    def test_get_github_username(self):
        sampler = IdSampler()
        username = sampler.get_github_username()
        assert isinstance(username, basestring)
        assert len(username) > 0, username
