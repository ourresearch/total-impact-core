from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderClientError, ProviderServerError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/mendeley")
SAMPLE_EXTRACT_UUID_PAGE = os.path.join(datadir, "uuidlookup")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE

TEST_DOI = "10.1038/nature10658"  # matches UUID sample page

class TestMendeley(ProviderTestCase):

    provider_name = "mendeley"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_metrics = [("title", "This is a title"), ("doi", TEST_DOI)]
    testitem_metrics_dict = {"title": ["This is a title"], "doi":[TEST_DOI]}

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(metrics_dict["mendeley:readers"], 102)

    def test_extract_provenance_url(self):
        f = open(SAMPLE_EXTRACT_PROVENANCE_URL_PAGE, "r")
        provenance_url = self.provider._extract_provenance_url(f.read())
        assert_equals(provenance_url, "http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/")

    def test_get_uuid_from_title(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE, "r")
        uuid = self.provider._get_uuid_from_title(self.testitem_metrics_dict["doi"][0], f.read())
        expected = "1f471f70-1e4f-11e1-b17d-0024e8453de6"
        assert_equals(uuid, expected)

    def test_get_uuid_from_title(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE, "r")
        uuid = self.provider._get_uuid_from_title(self.testitem_metrics_dict["doi"][0], f.read())
        expected = "1f471f70-1e4f-11e1-b17d-0024e8453de6"
        assert_equals(uuid, expected)

    def test__get_metrics_and_drilldown_from_uuid(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        response = self.provider._get_metrics_and_drilldown_from_uuid(f.read())
        expected = {'mendeley:discipline': ([{'id': 3, 'value': 80, 'name': 'Biological Sciences'}, {'id': 19, 'value': 14, 'name': 'Medicine'}, {'id': 22, 'value': 2, 'name': 'Psychology'}], 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:country': ([{'name': 'United States', 'value': 42}, {'name': 'Japan', 'value': 12}, {'name': 'United Kingdom', 'value': 9}], 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:career_stage': ([{'name': 'Ph.D. Student', 'value': 31}, {'name': 'Post Doc', 'value': 21}, {'name': 'Professor', 'value': 7}], 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:readers': (102, 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/')}
        assert_equals(response, expected)

    @nottest
    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'mendeley:discipline': ([{u'id': 3, u'value': 89, u'name': u'Biological Sciences'}, {u'id': 12, u'value': 7, u'name': u'Environmental Sciences'}, {u'id': 7, u'value': 4, u'name': u'Earth Sciences'}], u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:country': ([{u'name': u'Brazil', u'value': 24}, {u'name': u'United States', u'value': 23}, {u'name': u'United Kingdom', u'value': 7}], u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:career_stage': ([{u'name': u'Ph.D. Student', u'value': 31}, {u'name': u'Post Doc', u'value': 14}, {u'name': u'Student (Master)', u'value': 12}], u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:groups': (7, u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/'), 'mendeley:readers': (173, u'http://api.mendeley.com/research/amazonian-amphibian-diversity-is-primarily-derived-from-late-miocene-andean-lineages/')}
        print metrics_dict
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 
        # can't tell more about dicsciplines etc because they are percentages and may go up or down

    # override common tests
    @raises(ProviderClientError, ProviderServerError)
    def test_provider_metrics_400(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = common.get_400
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderServerError)
    def test_provider_metrics_500(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = common.get_500
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_empty(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = common.get_empty
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_txt(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = common.get_nonsense_txt
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_xml(self):
        if not self.provider.provides_metrics:
            raise SkipTest
        Provider.http_get = common.get_nonsense_xml
        metrics = self.provider.metrics(self.testitem_metrics)

