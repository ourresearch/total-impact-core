from totalimpact.models import Item, ItemFactory, Aliases
from totalimpact.config import Configuration
from totalimpact.providers.wikipedia import Wikipedia
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError, ProviderContentMalformedError, ProviderHttpError, ProviderValidationFailedError
from nose.tools import assert_equals, raises
import os, unittest, json, re

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

CWD, _ = os.path.split(__file__)

XML_DOC = os.path.join(CWD, "wikipedia_response.xml")
EMPTY_DOC = os.path.join(CWD, "wikipedia_empty_response.xml")
INCORRECT_DOC = os.path.join(CWD, "wikipedia_incorrect_response.xml")
CONFIG_FILENAME = "totalimpact/providers/wikipedia.conf.json"
TEST_URL = "http://www.example.com"

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

class Test_Wikipedia(unittest.TestCase):

    def setUp(self):
        self.old_http_get = Provider.http_get
        self.config = Configuration(CONFIG_FILENAME, False)
        self.provider = Wikipedia(self.config)

        self.metric_names = [
            "wikipedia:mentions",
            "foo:bar"
            ]
        self.simple_item = ItemFactory.make("not a dao", self.metric_names)

   
    def tearDown(self):
        Provider.http_get = self.old_http_get
    
    def test_implements_interface(self):
        
        # must have the four core methods
        assert hasattr(self.provider, "member_items")
        assert hasattr(self.provider, "aliases")
        assert hasattr(self.provider, "metrics")
        assert hasattr(self.provider, "provides_metrics")

  
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
        res = self.provider._extract_stats(f.read())
        assert_equals(res["wikipedia:mentions"], 0)


    def test_metrics_http_success(self):
        self.provider.http_get = successful_get
        
        self.simple_item.aliases.add_alias("doi", "10.1371/journal.pcbi.1000361")
        self.simple_item.aliases.add_alias("url", "http://cottagelabs.com")

        new_item = self.provider.metrics(self.simple_item)
        
        assert_equals(len(new_item.metrics), len(self.metric_names))
        assert_equals(len(new_item.metrics["wikipedia:mentions"]['values']), 1)
        assert_equals(new_item.metrics["wikipedia:mentions"]['values'].keys()[0], 1)

    def test_no_aliases_returns_item(self):
        self.provider.http_get = successful_get
        new_item = self.provider.metrics(self.simple_item)
        assert_equals(new_item, self.simple_item)

    @raises(ProviderClientError)
    def test_metrics_http_400(self):
        self.provider.http_get = get_400
        self.simple_item.aliases.add_alias("doi", "10.1371/journal.pcbi.1000361")
        new_item = self.provider.metrics(self.simple_item)

    @raises(ProviderServerError)
    def test_11_metrics_500(self):
        Provider.http_get = get_500
        self.simple_item.aliases.add_alias("doi", "10.1371/journal.pcbi.1000361")
        new_item = self.provider.metrics(self.simple_item)
