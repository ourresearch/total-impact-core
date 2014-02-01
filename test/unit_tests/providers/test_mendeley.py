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
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_BIBLIO_PAGE_OAI = os.path.join(datadir, "biblio_oai")

TEST_DOI = "10.1038/nature10658"  # matches UUID sample page

class TestMendeley(ProviderTestCase):

    provider_name = "mendeley"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_aliases_biblio_no_doi =  ("biblio", {'title': 'Scientometrics 2.0: Toward new metrics of scholarly impact on the social Web', 'first_author': 'Priem', 'journal': 'First Monday', 'number': '7', 'volume': '15', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': '2010'})
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
  
    def test_extract_biblio_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        metrics_dict = self.provider._extract_biblio(f.read())
        expected = {'is_oa_journal': 'False'}
        assert_equals(metrics_dict, expected)

    def test_extract_biblio_oai_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE_OAI, "r")
        metrics_dict = self.provider._extract_biblio(f.read())
        expected = {'oai_id': 'oai:arXiv.org:1012.4872', 'is_oa_journal': 'None'}
        assert_equals(metrics_dict, expected)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(metrics_dict["mendeley:readers"], 102)

    def test_extract_provenance_url(self):
        f = open(SAMPLE_EXTRACT_PROVENANCE_URL_PAGE, "r")
        provenance_url = self.provider._extract_provenance_url(f.read())
        assert_equals(provenance_url, "http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/")

    def test_get_ids_from_title(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE, "r")
        response = self.provider._get_uuid_from_title(self.testitem_metrics_dict, f.read())
        expected = {'uuid': '1f471f70-1e4f-11e1-b17d-0024e8453de6'}
        assert_equals(response, expected)

    def test_get_ids_from_title_no_doi(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE_NO_DOI, "r")
        response = self.provider._get_uuid_from_title(self.testitem_metrics_dict, f.read())
        print response
        expected = {'url': 'http://www.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/', 'uuid': '1f471f70-1e4f-11e1-b17d-0024e8453de6'}
        assert_equals(response, expected)

    def test_get_ids_from_title_no_doi_wrong_year(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE_NO_DOI, "r")
        response = self.provider._get_uuid_from_title(self.testitem_metrics_dict_wrong_year, f.read())
        expected = None
        assert_equals(response, expected)

    def test_get_metrics_and_drilldown_from_metrics_page(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        response = self.provider._get_metrics_and_drilldown_from_metrics_page(f.read())
        expected = {'mendeley:discipline': ([{'id': 3, 'value': 80, 'name': 'Biological Sciences'}, {'id': 19, 'value': 14, 'name': 'Medicine'}, {'id': 22, 'value': 2, 'name': 'Psychology'}], 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:country': ([{'name': 'United States', 'value': 42}, {'name': 'Japan', 'value': 12}, {'name': 'United Kingdom', 'value': 9}], 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:career_stage': ([{'name': 'Ph.D. Student', 'value': 31}, {'name': 'Post Doc', 'value': 21}, {'name': 'Professor', 'value': 7}], 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:readers': (102, 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/')}
        assert_equals(response, expected)

    def test_remove_punctuation(self):
        response = self.provider.remove_punctuation(u"sdflkdsjf4r42432098@#$#@$sdlkfj..sdfsdf")
        assert_equals(response, u'sdflkdsjf4r42432098sdlkfjsdfsdf')

    @http
    def test_metrics_pmid(self):
        # at the moment this item 
        metrics_dict = self.provider.metrics([("pmid", "12578738")])
        expected = {'mendeley:discipline': ([{u'id': 6, u'value': 33, u'name': u'Computer and Information Science'}, {u'id': 3, u'value': 33, u'name': u'Biological Sciences'}, {u'id': 19, u'value': 12, u'name': u'Medicine'}], u'http://api.mendeley.com/catalog/value-data/'), 
                'mendeley:country': ([{u'name': u'United States', u'value': 22}, {u'name': u'United Kingdom', u'value': 16}, {u'name': u'Netherlands', u'value': 12}], u'http://api.mendeley.com/catalog/value-data/'), 
                'mendeley:career_stage': ([{u'name': u'Ph.D. Student', u'value': 19}, {u'name': u'Other Professional', u'value': 15}, {u'name': u'Researcher (at an Academic Institution)', u'value': 14}], u'http://api.mendeley.com/catalog/value-data/'), 
                'mendeley:readers': (129, u'http://api.mendeley.com/catalog/value-data/')}
        print metrics_dict
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 
        # can't tell more about dicsciplines etc because they are percentages and may go up or down

    @http
    def test_metrics_arxiv(self):
        # at the moment this item 
        metrics = self.provider.metrics([("arxiv", "1203.4745")])
        print metrics
        expected = {'mendeley:discipline': ([{u'id': 6, u'value': 34, u'name': u'Computer and Information Science'}, {u'id': 23, u'value': 23, u'name': u'Social Sciences'}, {u'id': 19, u'value': 10, u'name': u'Medicine'}], u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), 'mendeley:country': ([{u'name': u'United States', u'value': 16}, {u'name': u'United Kingdom', u'value': 9}, {u'name': u'Germany', u'value': 5}], u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), 'mendeley:career_stage': ([{u'name': u'Librarian', u'value': 26}, {u'name': u'Ph.D. Student', u'value': 14}, {u'name': u'Other Professional', u'value': 14}], u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), 'mendeley:readers': (153, u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/')}
        assert_equals(metrics, expected)

    @http
    def test_aliases_no_doi(self):
        # at the moment this item 
        new_aliases = self.provider.aliases([self.testitem_aliases_biblio_no_doi])
        print new_aliases
        expected = [('doi', u'10.5210/fm.v15i7.2874'), ('url', u'http://www.mendeley.com/catalog/scientometrics-20-toward-new-metrics-scholarly-impact-social-web/'), ('uuid', u'f3018369-0eb4-3dbe-a3cc-9ee0bbc4e59e')]
        assert_equals(new_aliases, expected)

    @http
    def test_aliases_biblio(self):
        # at the moment this item 
        alias = (u'biblio', {u'title': u'Altmetrics in the wild: Using social media to explore scholarly impact', u'first_author': u'Priem', u'journal': u'arXiv preprint arXiv:1203.4745', u'authors': u'Priem, Piwowar, Hemminger', u'number': u'', u'volume': u'', u'first_page': u'', u'year': u'2012'})
        new_aliases = self.provider.aliases([alias])
        print new_aliases
        expected = [('doi', u'http://arxiv.org/abs/1203.4745v1'), ('url', u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), ('uuid', u'920cf7e1-02c1-3c40-bd52-18552089248e')]
        assert_equals(new_aliases, expected)

    # override common tests
    @raises(ProviderClientError, ProviderServerError)
    def test_provider_metrics_400(self):
        Provider.http_get = common.get_400
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderServerError)
    def test_provider_metrics_500(self):
        Provider.http_get = common.get_500
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_aliases_400(self):
        Provider.http_get = common.get_400
        metrics = self.provider.aliases([self.testitem_aliases_biblio_no_doi])

    @raises(ProviderServerError)
    def test_provider_aliases_500(self):
        Provider.http_get = common.get_500
        metrics = self.provider.aliases([self.testitem_aliases_biblio_no_doi])

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_empty(self):
        Provider.http_get = common.get_empty
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_txt(self):
        Provider.http_get = common.get_nonsense_txt
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_xml(self):
        Provider.http_get = common.get_nonsense_xml
        metrics = self.provider.metrics(self.testitem_metrics)

    def test_provider_biblio_400(self):
        pass
    def test_provider_biblio_500(self):
        pass

