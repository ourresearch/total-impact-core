from totalimpact.models import Aliases, Item, ItemFactory
from totalimpact.config import Configuration
from totalimpact.providers.dryad import Dryad
from totalimpact.providers.provider import Provider, ProviderFactory
from totalimpact.providers.provider import ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError
from totalimpact.providers.provider import ProviderHttpError, ProviderContentMalformedError, ProviderValidationFailedError

import os, unittest
import simplejson
from nose.tools import nottest, raises, assert_equals
import collections

from totalimpact.api import app

from test.provider import ProviderTestCase


# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content  

def get_member_items_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_member_items_html_zero_items(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS, "r")
    return DummyResponse(200, f.read())

def get_aliases_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
    return DummyResponse(200, f.read())

def get_metrics_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
    return DummyResponse(200, f.read())

def get_biblio_html_success(self, url, headers=None, timeout=None):
    f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
    return DummyResponse(200, f.read())


datadir = os.path.join(os.path.split(__file__)[0], "../../data/dryad")

DRYAD_CONFIG_FILENAME = "totalimpact/providers/dryad.conf.json"
TEST_DRYAD_DOI = "10.5061/dryad.7898"
TEST_DRYAD_AUTHOR = "Piwowar, Heather A."
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, 
    "sample_extract_metrics_page.html")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, 
    "sample_extract_aliases_page.xml")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, 
    "sample_extract_member_items_page.xml")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS = os.path.join(datadir, 
    "sample_extract_member_items_page_zero_items.xml")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, 
    "sample_extract_biblio_page.xml")
EXPECTED_PROVENANCE_URL = "http://dx.doi.org/10.5061/dryad.7898"
TEST_ALIASES_SEED = {"doi" : [TEST_DRYAD_DOI], "url" : ["http://datadryad.org/handle/10255/dryad.7898"]}


class TestDryad(ProviderTestCase):

    testitem_members = ("dryad_author", TEST_DRYAD_AUTHOR)
    testitem_aliases = ("doi", TEST_DRYAD_DOI)
    testitem_metrics = ("doi", TEST_DRYAD_DOI)
    testitem_biblio = ("doi", TEST_DRYAD_DOI)
    testitem_provenance_url = "http://dx.doi.org/10.5061/dryad.7898"

    provider_name = 'dryad'

    def setUp(self):
        ProviderTestCase.setUp(self)

        self.simple_item = ItemFactory.make("not a dao", app.config["PROVIDERS"])
        self.simple_item.aliases.add_alias("doi", TEST_DRYAD_DOI)

    def tearDown(self):
        Provider.http_get = self.old_http_get

    def test_01_is_relevant_id(self):
        # ensure that it matches an appropriate TEST_DRYAD_DOI
        assert not self.provider._is_relevant_id("11.12354/bib")
        # ensure that it doesn't match an inappropriate TEST_DRYAD_DOI
        assert not self.provider._is_relevant_id(("doi", "11.12354/bib"))
    
    def test_02a_member_items_success(self):
        Provider.http_get = get_member_items_html_success
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryad_author")
        assert len(members) == 4, str(members)
        assert_equals(members, [('doi', u'10.5061/dryad.j1fd7'), ('doi', u'10.5061/dryad.mf1sd'), ('doi', u'10.5061/dryad.3td2f'), ('doi', u'10.5061/dryad.j2c4g')])

    def test_02b_member_items_zero_items(self):
        Provider.http_get = get_member_items_html_zero_items
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryad_author")
        assert len(members) == 0, str(members)

    def test_03_extract_aliases(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = self.provider._extract_aliases(f.read())
        assert_equals(aliases, [('url', u'http://hdl.handle.net/10255/dryad.7898'), 
            ('title', u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides')])        

    def test_04a_get_aliases_success(self):
        """ Test alias expansion on doi:10.5061/dryad.7898 
            We should get two new aliases found, a url and a title
        """
        Provider.http_get = get_aliases_html_success
        aliases = self.simple_item.aliases.get_aliases_list(self.provider.alias_namespaces)
        new_aliases = self.provider.aliases(aliases)

        # Convert from tuple list into dict format (easier to work with here)
        aliases_dict = collections.defaultdict(list)
        for (k,v) in new_aliases: aliases_dict[k].append(v)
    
        assert_equals(set(aliases_dict.keys()), set(['url','title']))
        assert_equals(aliases_dict['url'], [u'http://hdl.handle.net/10255/dryad.7898'])
        assert_equals(aliases_dict['title'], [u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides'])

    def test_05b_basic_extract_stats(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        ret = self.provider._extract_stats(f.read())
        assert len(ret) == 3, ret

    def test_06a_get_metrics_success(self):
        Provider.http_get = get_metrics_html_success
        aliases = self.simple_item.aliases.get_aliases_list(self.provider.alias_namespaces)
        metrics = dict(self.provider.metrics(aliases))

        metrics_dict = dict(metrics)
        assert_equals(metrics_dict['dryad:most_downloaded_file'], 63)
        assert_equals(metrics_dict['dryad:package_views'], 149)
        assert_equals(metrics_dict['dryad:total_downloads'], 169)

    def test_06b_get_metrics_with_non_dryad_doi(self):
        """ test_06b_get_metrics_with_non_dryad_doi

            If the item has a DOI alias but it's not recognised by dryad, 
            then won't find any metrics. Should get a None returned.
        """
        self.simple_item.aliases.doi = ['11.12354/bib']
        aliases = self.simple_item.aliases.get_aliases_list(self.provider.alias_namespaces)
        metrics = self.provider.metrics(aliases)
        assert_equals(metrics, None)

    def test_07a_basic_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        assert_equals(ret, {'year': u'2010', 'title': u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides'})

    def test_07b_get_biblio_success(self):
        Provider.http_get = get_biblio_html_success
        aliases = self.simple_item.aliases.get_aliases_list(self.provider.biblio_namespaces)
        biblio_data = self.provider.biblio(aliases)
        assert_equals(biblio_data['year'], u'2010')
        assert_equals(biblio_data['title'], u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides')

    def test_get_provenance_url(self):
        metric_name = "example_metric_name"
        aliases = self.simple_item.aliases.get_aliases_list(self.provider.biblio_namespaces)
        response = self.provider.provenance_url(metric_name, aliases)
        assert_equals(response, self.testitem_provenance_url)

        # If no doi then return None
        response = self.provider.provenance_url(metric_name, [("url", "someurl")])
        assert_equals(response, None)
