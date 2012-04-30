from totalimpact.models import Aliases, Item, ItemFactory
from totalimpact.config import Configuration
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.providers.provider import ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError
from totalimpact.providers.provider import ProviderHttpError, ProviderContentMalformedError, ProviderValidationFailedError

import os, unittest
import simplejson
from nose.tools import nottest, raises, assert_equals
from nose.plugins.skip import SkipTest

from totalimpact.api import app

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content  

def get_member_items_html_success(self, url, headers=None, timeout=None, error_conf=None):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_member_items_html_zero_items(self, url, headers=None, timeout=None, error_conf=None):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS, "r")
    return DummyResponse(200, f.read())

def get_aliases_html_success(self, url, headers=None, timeout=None, error_conf=None):
    f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())

def get_metrics_html_success(self, url, headers=None, timeout=None, error_conf=None):
    f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_biblio_html_success(self, url, headers=None, timeout=None, error_conf=None):
    f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
    return DummyResponse(200, f.read())

def get_nonsense_xml(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(200, '<?xml version="1.0" encoding="UTF-8"?><nothingtoseehere>nonsense</nothingtoseehere>')

def get_nonsense_txt(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(200, "nonsense")

def get_empty(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(200, "")

def get_400(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(400, "")

def get_500(self, url, headers=None, timeout=None, error_conf=None):
    return DummyResponse(500, "")


class ProviderTestCase:
    """ Base class to help in writing tests of providers

        To this class effectively, use it as the base class of your
        provider test and set self.provider to point to an instance
        of the provider you want to test.

        You also want to set the following so there is a suitable
        aliase which will be passed to aliases and metrics for testing.

          self.testitem_aliases = ('ns','val')
          self.testitem_metrics = ('ns','val')

        This test will ensure the following properties are covered:

          * Signature is fully defined
          * aliases method handles http errors correctly
          * metrics method handles http errors correctly
          * member_items method handles http errors correctly
          * biblio method handles http errors correctly
    
        The setup and tear down methods will do some temporary saves
        for monkey-patching, which allows you to replace 
        provider.http_get safely in your tests, if required.
        """

    def setUp(self):
        self.provider = ProviderFactory.get_provider(app.config["PROVIDERS"][self.provider_name])
        self.old_http_get = Provider.http_get

    def tearDown(self):
        Provider.http_get = self.old_http_get

    def test_0001_testcase_interface(self):
        """ test_provider_testcase_interface

            Ensure that this class has defined everything needed.
        """
        assert hasattr(self, "testitem_aliases")
        assert hasattr(self, "testitem_metrics")
        assert hasattr(self, "testitem_biblio")

    def test_0002_provider_base_setup(self):
        """ test_provider_base_setup
             
            ensure that the configuration is valid
        """
        assert self.provider.config is not None
        assert self.provider.provider_name is not None

    def test_0003_provider_interface(self):
        """ test_provider_interface

            Ensure that the implementation has all the relevant provider 
            definition fields defined.
        """
        # Function methods (may return NotImplementedError)
        assert hasattr(self.provider, "member_items")
        assert hasattr(self.provider, "aliases")
        assert hasattr(self.provider, "metrics")

        # Class members for provider definition
        assert hasattr(self.provider, "provides_members")
        assert hasattr(self.provider, "provides_aliases")
        assert hasattr(self.provider, "provides_metrics")
        assert hasattr(self.provider, "provides_biblio")

        assert hasattr(self.provider, "provider_name")
        assert hasattr(self.provider, "metric_names")

        assert hasattr(self.provider, "member_types")
        assert hasattr(self.provider, "metric_namespaces")
        assert hasattr(self.provider, "alias_namespaces")
        assert hasattr(self.provider, "biblio_namespaces")

    ###################################################################
    ##
    ## Check member_items method 
    ##

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_member_items_400(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_400
        (query_type, query_string) = self.testitem_members 
        members = self.provider.member_items(query_string, query_type)

    @raises(ProviderServerError)
    def test_provider_member_items_500(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_500
        (query_type, query_string) = self.testitem_members 
        members = self.provider.member_items(query_string, query_type)

    @raises(ProviderContentMalformedError)
    def test_provider_member_items_empty(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_empty
        (query_type, query_string) = self.testitem_members 
        members = self.provider.member_items(query_string, query_type)

    @raises(ProviderContentMalformedError)
    def test_provider_member_items_nonsense_txt(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        (query_type, query_string) = self.testitem_members 
        members = self.provider.member_items(query_string, query_type)

    @raises(ProviderContentMalformedError)
    def test_provider_member_items_nonsense_xml(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_nonsense_xml
        (query_type, query_string) = self.testitem_members 
        members = self.provider.member_items(query_string, query_type)

    ###################################################################
    ##
    ## Check aliases method 
    ##

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_aliases_400(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_400
        new_aliases = self.provider.aliases([self.testitem_aliases])

    @raises(ProviderServerError)
    def test_provider_aliases_500(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_500
        new_aliases = self.provider.aliases([self.testitem_aliases])

    @raises(ProviderContentMalformedError)
    def test_provider_aliases_empty(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_empty
        new_aliases = self.provider.aliases([self.testitem_aliases])

    @raises(ProviderContentMalformedError)
    def test_provider_nonsense_txt(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        new_aliases = self.provider.aliases([self.testitem_aliases])

    @raises(ProviderContentMalformedError)
    def test_provider_nonsense_xml(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_nonsense_xml
        new_aliases = self.provider.aliases([self.testitem_aliases])

    ###################################################################
    ##
    ## Check metrics method
    ##

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_metrics_400(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = get_400
        metrics = self.provider.metrics([self.testitem_metrics])

    @raises(ProviderServerError)
    def test_provider_metrics_500(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = get_500
        metrics = self.provider.metrics([self.testitem_metrics])

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_empty(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = get_empty
        metrics = self.provider.metrics([self.testitem_metrics])

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_txt(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        metrics = self.provider.metrics([self.testitem_metrics])

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_xml(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = get_nonsense_xml
        metrics = self.provider.metrics([self.testitem_metrics])

    ###################################################################
    ##
    ## Check biblio method
    ##

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_biblio_400(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_400
        biblio = self.provider.biblio([self.testitem_biblio])

    @raises(ProviderServerError)
    def test_provider_biblio_500(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_500
        biblio = self.provider.biblio([self.testitem_biblio])

    @raises(ProviderContentMalformedError)
    def test_provider_biblio_empty(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_empty
        biblio = self.provider.biblio([self.testitem_biblio])

    @raises(ProviderContentMalformedError)
    def test_provider_biblio_nonsense_txt(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        biblio = self.provider.biblio([self.testitem_biblio])

    @raises(ProviderContentMalformedError)
    def test_provider_biblio_nonsense_xml(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_nonsense_xml
        biblio = self.provider.biblio([self.testitem_biblio])
        

