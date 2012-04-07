from totalimpact.models import Metrics, Aliases, Item
from totalimpact.config import Configuration
from totalimpact.providers.dryad import Dryad
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest
import simplejson
from nose.tools import nottest, raises, assert_equals


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

def get_nonsense_xml(self, url, headers=None, timeout=None):
    return DummyResponse(200, '<?xml version="1.0" encoding="UTF-8"?><nothingtoseehere>nonsense</nothingtoseehere>')

def get_nonsense_txt(self, url, headers=None, timeout=None):
    return DummyResponse(200, "nonsense")

def get_empty(self, url, headers=None, timeout=None):
    return DummyResponse(200, "")

def get_400(self, url, headers=None, timeout=None):
    return DummyResponse(400, "")

def get_500(self, url, headers=None, timeout=None):
    return DummyResponse(500, "")


CWD, _ = os.path.split(__file__)

DRYAD_CONFIG_FILENAME = "totalimpact/providers/dryad.conf.json"
TEST_DRYAD_DOI = "10.5061/dryad.7898"
TEST_DRYAD_AUTHOR = "Piwowar, Heather A."
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(CWD, "sample_extract_metrics_page.html")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(CWD, "sample_extract_aliases_page.xml")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(CWD, "sample_extract_member_items_page.xml")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE_ZERO_ITEMS = os.path.join(CWD, "sample_extract_member_items_page_zero_items.xml")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(CWD, "sample_extract_biblio_page.xml")

TEST_ALIASES_SEED = {"doi" : [TEST_DRYAD_DOI], "url" : ["http://datadryad.org/handle/10255/dryad.7898"]}


class Test_Dryad(unittest.TestCase):

    def setUp(self):
        self.old_http_get = Provider.http_get
        self.config = Configuration(DRYAD_CONFIG_FILENAME, False)
        self.provider = Dryad(self.config)

        a = Aliases()
        a.add_alias("doi", TEST_DRYAD_DOI)
        self.simple_item = Item("12345", "not a dao")
        self.simple_item.aliases = a


    def tearDown(self):
        Provider.http_get = self.old_http_get
    

    def test_01_init(self):
        # ensure that the configuration is valid
        assert self.provider.config is not None
        assert self.provider.state is not None
        assert self.provider.id == "Dryad"
        

    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        # must have the four core methods
        assert hasattr(self.provider, "member_items")
        assert hasattr(self.provider, "aliases")
        assert hasattr(self.provider, "metrics")
        assert hasattr(self.provider, "provides_metrics")
    

    def test_03_is_relevant_id(self):
        # ensure that it matches an appropriate TEST_DRYAD_DOI
        assert not self.provider._is_relevant_id("11.12354/bib")
        
        # ensure that it doesn't match an inappropriate TEST_DRYAD_DOI
        assert not self.provider._is_relevant_id(("doi", "11.12354/bib"))
    

    def test_04a_member_items_success(self):
        Provider.http_get = get_member_items_html_success
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 4, str(members)
        assert_equals(members, [('doi', u'10.5061/dryad.j1fd7'), ('doi', u'10.5061/dryad.mf1sd'), ('doi', u'10.5061/dryad.3td2f'), ('doi', u'10.5061/dryad.j2c4g')])

    def test_04f_member_items_zero_items(self):
        Provider.http_get = get_member_items_html_zero_items
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 0, str(members)

    @raises(ProviderClientError)
    def test_04b_member_items_400(self):
        Provider.http_get = get_400
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")

    @raises(ProviderServerError)
    def test_04c_member_items_500(self):
        Provider.http_get = get_500
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")

    @raises(ProviderClientError)
    def test_04d_member_items_empty(self):
        Provider.http_get = get_empty
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")

    @raises(ProviderClientError)
    def test_04g_member_items_nonsense_txt(self):
        Provider.http_get = get_nonsense_txt
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 0, str(members)

    @raises(ProviderClientError)
    def test_04h_member_items_nonsense_xml(self):
        Provider.http_get = get_nonsense_xml
        members = self.provider.member_items(TEST_DRYAD_AUTHOR, "dryadAuthor")
        assert len(members) == 0, str(members)



    def test_05_extract_aliases(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = self.provider._extract_aliases(f.read())
        assert_equals(aliases, [('url', u'http://hdl.handle.net/10255/dryad.7898'), 
            ('title', u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides')])        

    def test_05a_get_aliases_success(self):
        Provider.http_get = get_aliases_html_success
        item_with_new_aliases = self.provider.aliases(self.simple_item)

        new_aliases = item_with_new_aliases.aliases
        assert_equals(new_aliases.get_aliases_dict().keys(), ['url', 'tiid', 'doi', 'title'])
        assert_equals(new_aliases.get_ids_by_namespace(Aliases.NS.URL), [u'http://hdl.handle.net/10255/dryad.7898'])
        assert_equals(new_aliases.get_ids_by_namespace(Aliases.NS.DOI), ['10.5061/dryad.7898'])
        assert_equals(new_aliases.get_ids_by_namespace(Aliases.NS.TITLE), [u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides'])
        
    # zero items doesn't make sense for dryad aliases becauase will always have a url if a valid page

    @raises(ProviderClientError)
    def test_05b_aliases_400(self):
        Provider.http_get = get_400
        item_with_new_aliases = self.provider.aliases(self.simple_item)

    @raises(ProviderServerError)
    def test_05c_aliases_500(self):
        Provider.http_get = get_500
        item_with_new_aliases = self.provider.aliases(self.simple_item)

    @raises(ProviderClientError)
    def test_05d_aliases_empty(self):
        Provider.http_get = get_empty
        item_with_new_aliases = self.provider.aliases(self.simple_item)

    @raises(ProviderClientError)
    def test_05g_nonsense_txt(self):
        Provider.http_get = get_nonsense_txt
        item_with_new_aliases = self.provider.aliases(self.simple_item)
        assert len(item_with_new_aliases.aliases.get_aliases_dict().keys()) == 0, str(item_with_new_aliases)

    @raises(ProviderClientError)
    def test_05h_nonsense_xml(self):
        Provider.http_get = get_nonsense_xml
        item_with_new_aliases = self.provider.aliases(self.simple_item)
        assert len(item_with_new_aliases.aliases.get_aliases_dict().keys()) == 0, str(item_with_new_aliases)    
    


    def test_06a_provides_metrics(self):
        assert self.provider.provides_metrics() == True

    def test_06b_show_details_url(self):
        assert self.provider.get_show_details_url(TEST_DRYAD_DOI) == "http://dx.doi.org/" + TEST_DRYAD_DOI
    

    def test_06c_basic_extract_stats(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        ret = self.provider._extract_stats(f.read())
        assert len(ret) == 4, ret

    def test_07a_get_metrics_success(self):
        Provider.http_get = get_metrics_html_success
        item_with_new_metrics = self.provider.metrics(self.simple_item)

        new_metrics = item_with_new_metrics.data["bucket"]
        new_metrics_values = [(m["id"], m["value"]) for m in new_metrics.values()]
        new_metrics_values.sort()  # for consistent order
        assert_equals(new_metrics_values,
            [('Dryad:file_views', 268), ('Dryad:most_downloaded_file', 76), ('Dryad:package_views', 407), ('Dryad:total_downloads', 178)])

    @raises(ProviderClientError)
    def test_07b_metrics_400(self):
        Provider.http_get = get_400
        item_with_new_metrics = self.provider.metrics(self.simple_item)

    @raises(ProviderServerError)
    def test_07c_metrics_500(self):
        Provider.http_get = get_500
        item_with_new_metrics = self.provider.metrics(self.simple_item)

    @raises(ProviderClientError)
    def test_07d_metrics_empty(self):
        Provider.http_get = get_empty
        item_with_new_metrics = self.provider.metrics(self.simple_item)

    @raises(ProviderClientError)
    def test_07g_metrics_nonsense_txt(self):
        Provider.http_get = get_nonsense_txt
        item_with_new_metrics = self.provider.metrics(self.simple_item)
        assert_equals(len(item_with_new_metrics.data["bucket"]) == 0)

    @raises(ProviderClientError)
    def test_07h_metrics_nonsense_xml(self):
        Provider.http_get = get_nonsense_xml
        item_with_new_metrics = self.provider.metrics(self.simple_item)
        assert_equals(len(item_with_new_metrics.data["bucket"]) == 0)


    def test_08_provides_biblio(self):
        assert self.provider.provides_biblio() == True

    def test_09a_basic_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        assert_equals(ret, {'year': u'2010', 'title': u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides'})

    def test_09b_get_biblio_success(self):
        Provider.http_get = get_biblio_html_success
        biblio_object = self.provider.biblio(self.simple_item)
        assert_equals(biblio_object.data, {'year': u'2010', 'title': u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides'})

    @raises(ProviderClientError)
    def test_09c_biblio_400(self):
        Provider.http_get = get_400
        biblio_object = self.provider.biblio(self.simple_item)

    @raises(ProviderServerError)
    def test_09d_biblio_500(self):
        Provider.http_get = get_500
        biblio_object = self.provider.biblio(self.simple_item)

    @raises(ProviderClientError)
    def test_09e_biblio_empty(self):
        Provider.http_get = get_empty
        biblio_object = self.provider.biblio(self.simple_item)

    @raises(ProviderClientError)
    def test_09f_biblio_nonsense_txt(self):
        Provider.http_get = get_nonsense_txt
        biblio_object = self.provider.biblio(self.simple_item)

    @raises(ProviderClientError)
    def test_09g_biblio_nonsense_xml(self):
        Provider.http_get = get_nonsense_xml
        biblio_object = self.provider.biblio(self.simple_item)
        

