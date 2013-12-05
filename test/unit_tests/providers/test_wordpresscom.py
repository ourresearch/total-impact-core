from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/wordpresscom")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestWordpresscom(ProviderTestCase):

    provider_name = "wordpresscom"

    api_key = os.environ["WORDPRESS_OUR_BLOG_API_KEY"]
    testitem_members = {"blogUrl": "http://researchremix.wordpress.com", "apiKey": api_key}
    testitem_aliases = ("blog", '{"url": "http://researchremix.wordpress.com", "api_key": "'+api_key+'"}')
    testitem_metrics = ("blog", '{"url": "http://researchremix.wordpress.com", "api_key": "'+api_key+'"}')
    testitem_biblio = ("blog", '{"url": "http://researchremix.wordpress.com", "api_key": "'+api_key+'"}')

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A WORDPRESS ID")), False)
  

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("github:forks", [self.testitem_aliases])
        assert_equals(provenance_url, u'http://researchremix.wordpress.com')


    def test_members(self):
        response = self.provider.member_items(self.testitem_members)
        print response
        expected = [('blog', '{"url": "http://researchremix.wordpress.com", "api_key": "'+self.api_key+'"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2013/05/11/society-oa-options/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/05/29/non-american-please-sign/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2013/03/05/why-google-isnt-good-enough-for-academic-search/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/03/05/talking-text-mining-with-elsevier/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2013/03/13/why-google/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/01/31/31-flavours/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2011/02/18/early_results/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/01/07/rwa-job-losses/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/05/29/dear-research-data-advocate-please-sign-the-petition-oamonday/", "api_key": "'+self.api_key+'", "blog_url": "researchremix.wordpress.com"}')]
        assert_equals(response, expected)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'wordpresscom:views': (74942, u'http://researchremix.wordpress.com'), 'wordpresscom:subscribers': (66, u'http://researchremix.wordpress.com')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'url': u'http://researchremix.wordpress.com', 'account': u'http://researchremix.wordpress.com', 'description': u'Blogging about the science, engineering, and human factors of biomedical research data reuse', 'is_account': True, 'title': u'Research Remix'}
        assert_equals(biblio_dict.keys(), expected.keys())
        for key in ["url", "title", "description"]:
            assert_equals(biblio_dict[key], expected[key])

    # not relevant given library approach

    def test_provider_member_items_400(self):
        pass
    def test_provider_member_items_500(self):
        pass
    def test_provider_member_items_empty(self):
        pass
    def test_provider_member_items_nonsense_txt(self):
        pass
    def test_provider_member_items_nonsense_xml(self):
        pass

    def test_provider_aliases_400(self):
        pass
    def test_provider_aliases_500(self):
        pass

