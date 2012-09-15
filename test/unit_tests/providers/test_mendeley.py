from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderClientError, ProviderServerError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/mendeley")
SAMPLE_EXTRACT_UUID_PAGE = os.path.join(datadir, "uuidlookup")
SAMPLE_EXTRACT_UUID_PAGE_NO_DOI = os.path.join(datadir, "uuidlookup_no_doi")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE

TEST_DOI = "10.1038/nature10658"  # matches UUID sample page

class TestMendeley(ProviderTestCase):

    provider_name = "mendeley"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_metrics_dict = {"biblio":[{"year":2011, "authors":"sdf", "title": "Mutations causing syndromic autism define an axis of synaptic pathophysiology"}],"doi":[TEST_DOI]}
    testitem_metrics = [(k, v[0]) for (k, v) in testitem_metrics_dict.items()]
    testitem_metrics_dict_wrong_year = {"biblio":[{"year":9999, "authors":"sdf", "title": "Mutations causing syndromic autism define an axis of synaptic pathophysiology"}],"doi":[TEST_DOI]}
    testitem_metrics_wrong_year = [(k, v[0]) for (k, v) in testitem_metrics_dict_wrong_year.items()]

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
        uuid = self.provider._get_uuid_from_title(self.testitem_metrics_dict, f.read())
        expected = "1f471f70-1e4f-11e1-b17d-0024e8453de6"
        assert_equals(uuid, expected)

    def test_get_uuid_from_title_no_doi(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE_NO_DOI, "r")
        uuid = self.provider._get_uuid_from_title(self.testitem_metrics_dict, f.read())
        expected = "1f471f70-1e4f-11e1-b17d-0024e8453de6"
        assert_equals(uuid, expected)

    def test_get_uuid_from_title_no_doi_wrong_year(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE_NO_DOI, "r")
        uuid = self.provider._get_uuid_from_title(self.testitem_metrics_dict_wrong_year, f.read())
        expected = None
        assert_equals(uuid, expected)

    def test__get_metrics_and_drilldown_from_uuid(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        response = self.provider._get_metrics_and_drilldown_from_uuid(f.read())
        expected = {'mendeley:discipline': ([{'id': 3, 'value': 80, 'name': 'Biological Sciences'}, {'id': 19, 'value': 14, 'name': 'Medicine'}, {'id': 22, 'value': 2, 'name': 'Psychology'}], 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:country': ([{'name': 'United States', 'value': 42}, {'name': 'Japan', 'value': 12}, {'name': 'United Kingdom', 'value': 9}], 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:career_stage': ([{'name': 'Ph.D. Student', 'value': 31}, {'name': 'Post Doc', 'value': 21}, {'name': 'Professor', 'value': 7}], 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:readers': (102, 'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/')}
        assert_equals(response, expected)

    def test_remove_punctuation(self):
        response = self.provider.remove_punctuation(u"sdflkdsjf4r42432098@#$#@$sdlkfj..sdfsdf")
        assert_equals(response, u'sdflkdsjf4r42432098sdlkfjsdfsdf')

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics(self.testitem_metrics)
        expected = {'mendeley:discipline': ([{u'id': 3, u'value': 80, u'name': u'Biological Sciences'}, {u'id': 19, u'value': 14, u'name': u'Medicine'}, {u'id': 22, u'value': 2, u'name': u'Psychology'}], u'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:country': ([{u'name': u'United States', u'value': 42}, {u'name': u'Japan', u'value': 12}, {u'name': u'United Kingdom', u'value': 9}], u'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:career_stage': ([{u'name': u'Ph.D. Student', u'value': 31}, {u'name': u'Post Doc', u'value': 21}, {u'name': u'Professor', u'value': 7}], u'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:readers': (102, u'http://api.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/')}
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

