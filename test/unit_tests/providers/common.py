from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.providers.provider import ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError
from totalimpact.providers.provider import ProviderHttpError, ProviderContentMalformedError, ProviderValidationFailedError

import os, unittest
import simplejson
from nose.tools import nottest, raises, assert_equals
from nose.plugins.skip import SkipTest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content  
        self.headers = {"header1":"header_value_1"}  

def get_member_items_html_success(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_member_items_html_zero_items(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS, "r")
    return DummyResponse(200, f.read())

def get_aliases_html_success(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())

def get_metrics_html_success(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_biblio_html_success(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
    return DummyResponse(200, f.read())

def get_nonsense_xml(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    return DummyResponse(200, '<?xml version="1.0" encoding="UTF-8"?><nothingtoseehere>nonsense</nothingtoseehere>')

def get_nonsense_txt(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    return DummyResponse(200, "nonsense")

def get_empty(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    return DummyResponse(200, "")

def get_400(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
    return DummyResponse(400, "")

def get_500(self, url, headers=None, timeout=None, error_conf=None, cache_enabled=True, allow_redirects=False):
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

    # overwrite in providers for supported methods
    testitem_aliases = ()
    testitem_metrics = ()
    testitem_biblio = ()

    def setUp(self):
        self.provider = ProviderFactory.get_provider(self.provider_name)
        self.old_http_get = Provider.http_get

    def tearDown(self):
        Provider.http_get = self.old_http_get

    def test_0003_provider_interface(self):
        """ test_provider_interface

            Ensure that the implementation has all the relevant provider 
            definition fields defined.
        """
        # Function methods (may return NotImplementedError)
        assert hasattr(self.provider, "member_items")
        assert hasattr(self.provider, "aliases")
        assert hasattr(self.provider, "metrics")
        assert hasattr(self.provider, "biblio")

        # Class members for provider definition
        assert hasattr(self.provider, "provides_members")
        assert hasattr(self.provider, "provides_aliases")
        assert hasattr(self.provider, "provides_metrics")
        assert hasattr(self.provider, "provides_biblio")
        assert hasattr(self.provider, "provides_static_meta")

        assert hasattr(self.provider, "provider_name")

    ###################################################################
    ##
    ## Check member_items method 
    ##

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_member_items_400(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_400
        members = self.provider.member_items(self.testitem_members)

    @raises(ProviderServerError)
    def test_provider_member_items_500(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_500
        members = self.provider.member_items(self.testitem_members)

    @raises(ProviderContentMalformedError)
    def test_provider_member_items_empty(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_empty
        members = self.provider.member_items(self.testitem_members)

    @raises(ProviderContentMalformedError)
    def test_provider_member_items_nonsense_txt(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        members = self.provider.member_items(self.testitem_members)

    @raises(ProviderContentMalformedError)
    def test_provider_member_items_nonsense_xml(self):
        if not self.provider.provides_members:
            raise SkipTest
        Provider.http_get = get_nonsense_xml
        members = self.provider.member_items(self.testitem_members)

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

    def test_provider_aliases_empty(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_empty
        aliases = self.provider.aliases([self.testitem_aliases])
        assert_equals(aliases, [])

    @nottest
    @raises(ProviderContentMalformedError)
    def test_provider_aliases_nonsense_txt(self):
        if not self.provider.provides_aliases:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        new_aliases = self.provider.aliases([self.testitem_aliases])

    @nottest
    @raises(ProviderContentMalformedError)
    def test_provider_aliases_nonsense_xml(self):
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

    @nottest
    @raises(ProviderContentMalformedError)
    def test_provider_biblio_empty(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_empty
        biblio = self.provider.biblio([self.testitem_biblio])

    @nottest
    @raises(ProviderContentMalformedError)
    def test_provider_biblio_nonsense_txt(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_nonsense_txt
        biblio = self.provider.biblio([self.testitem_biblio])

    @nottest
    @raises(ProviderContentMalformedError)
    def test_provider_biblio_nonsense_xml(self):
        if not self.provider.provides_biblio:
            raise SkipTest
        Provider.http_get = get_nonsense_xml
        biblio = self.provider.biblio([self.testitem_biblio])
        

