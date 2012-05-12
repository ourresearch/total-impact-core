from totalimpact.models import Aliases
from totalimpact.config import Configuration
from totalimpact.providers.github import Github
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content

def get_memberitems_user_html(self, url, headers=None, timeout=None):
    f = open(GITHUB_MEMBERITEMS_USER_HTML, "r")
    return DummyResponse(200, f.read())

def get_memberitems_orgs_html(self, url, headers=None, timeout=None):
    f = open(GITHUB_MEMBERITEMS_ORGS_HTML, "r")
    return DummyResponse(200, f.read())

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases

datadir = os.path.join(os.path.split(__file__)[0], "../../data/github")

GITHUB_MEMBERITEMS_USER_HTML = os.path.join(datadir, 
    "sample_extract_user_metrics.json")
GITHUB_MEMBERITEMS_ORGS_HTML = os.path.join(datadir, 
    "sample_extract_orgs_metrics.json")

DOI = "10.5061/dryad.7898"

from test.provider import ProviderTestCase

class TestGithub(ProviderTestCase):

    testitem_members = ("github", "egonw")
    testitem_aliases = ("github", "egonw")
    testitem_metrics = ("github", "egonw")
    testitem_biblio = ("github", "egonw")

    provider_name = 'github'

    def test_04_member_items(self):        
        Provider.http_get = get_memberitems_user_html
        members = self.provider.member_items("egonw", "github_user")
        assert len(members) >= 30, (len(members), members)

