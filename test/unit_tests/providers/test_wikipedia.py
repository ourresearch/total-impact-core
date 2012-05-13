from totalimpact.models import Item, ItemFactory, Aliases
from totalimpact.providers.wikipedia import Wikipedia

from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.providers.provider import ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError
from totalimpact.providers.provider import ProviderHttpError, ProviderContentMalformedError, ProviderValidationFailedError
from totalimpact.api import app
from test.unit_tests.providers.test_common import ProviderTestCase

from nose.tools import assert_equals, raises
import os, unittest, json, re, time

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content
def successful_get(url, headers=None, timeout=None, error_conf=None):
    f = open(XML_DOC, "r")
    return DummyResponse(200, f.read())
def get_400(url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(400, "")
def get_500(url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(500, "")
def exception_http_get(url, headers=None, timeout=None, error_conf=None):
    raise ProviderHttpError()

def extract_stats_content_malformed(self, content, metric):
    raise ProviderContentMalformedError()
def extract_stats_validation_error(self, content, metric):
    raise ProviderValidationFailedError()


# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases

datadir = os.path.join(os.path.split(__file__)[0], "../../data/wikipedia")

TEST_URL = "http://www.example.com"
XML_DOC = os.path.join(datadir, 
    "wikipedia_response.xml")
EMPTY_DOC = os.path.join(datadir, 
    "wikipedia_empty_response.xml")
INCORRECT_DOC = os.path.join(datadir, 
    "wikipedia_incorrect_response.xml")

ERROR_CONF = json.loads('''
{
    "timeout" : { "retries" : 1, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "http_error" : { "retries" : 1, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "content_malformed" : { "retries" : 1, "retry_delay" : 0, "retry_type" : "linear", "delay_cap" : -1 },
    "rate_limit_reached" : { },
    "client_server_error" : { },
    "validation_failed" : { }
}
''')

TEST_WIKIPEDIA_DOI = "10.1371/journal.pcbi.1000361"

class TestWikipedia(ProviderTestCase):

    testitem_members = None
    testitem_aliases = ("doi", TEST_WIKIPEDIA_DOI)
    testitem_metrics = ("doi", TEST_WIKIPEDIA_DOI)
    testitem_biblio = ("doi", TEST_WIKIPEDIA_DOI)

    provider_name = 'wikipedia'

    def setUp(self):
        ProviderTestCase.setUp(self)

        self.simple_item = ItemFactory.make("not a dao", app.config["PROVIDERS"])
  
    def test_metrics_extract_stats(self):
        f = open(XML_DOC, "r")
        good_page = f.read()
        res = self.provider._extract_stats(good_page)
        assert_equals(res["wikipedia:mentions"], 1)
       
        # now give it something with no results
        f = open(EMPTY_DOC, "r")
        res = self.provider._extract_stats(f.read())
        assert_equals(res["wikipedia:mentions"], 0)
        
        # now give it an invalid document
        f = open(INCORRECT_DOC, "r")
        try:
            self.provider._extract_stats(f.read())
            self.fail("Parsed incorrect document")
        except ProviderContentMalformedError, e:
            pass


    def test_metrics_http_success(self):
        self.provider.http_get = successful_get
        
        self.simple_item.aliases.add_alias("doi", "10.1371/journal.pcbi.1000361")
        self.simple_item.aliases.add_alias("url", "http://cottagelabs.com")

        aliases = self.simple_item.aliases.get_aliases_list(self.provider.metric_namespaces)
        metrics = self.provider.metrics(aliases)
        metric_dict = dict(metrics)
        
        assert_equals(len(metric_dict.keys()), len(self.provider.metric_names))
        assert_equals(metric_dict["wikipedia:mentions"], 1)


