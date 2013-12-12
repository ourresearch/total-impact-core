from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/wordpresscom")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestWordpresscom(ProviderTestCase):

    provider_name = "wordpresscom"

    api_key = os.environ["WORDPRESS_OUR_BLOG_API_KEY"]
    testitem_members = {"blogUrl": "http://researchremix.wordpress.com"}
    testitem_aliases = ("blog", "http://researchremix.wordpress.com")
    testitem_metrics = ("blog", "http://researchremix.wordpress.com")
    testitem_biblio = ("blog", "http://researchremix.wordpress.com")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A WORDPRESS ID")), False)
  

    def test_provenance_url(self):
        provenance_url = self.provider.provenance_url("wordpresscom:subscribers", [self.testitem_aliases])
        assert_equals(provenance_url, u'http://researchremix.wordpress.com')


    @http
    def test_members(self):
        response = self.provider.member_items(self.testitem_members)
        print response
        expected = [('blog', 'http://researchremix.wordpress.com'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2013/05/11/society-oa-options/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/05/29/non-american-please-sign/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2013/03/05/why-google-isnt-good-enough-for-academic-search/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/03/05/talking-text-mining-with-elsevier/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2013/03/13/why-google/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/01/31/31-flavours/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2011/02/18/early_results/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/05/29/dear-research-data-advocate-please-sign-the-petition-oamonday/", "blog_url": "http://researchremix.wordpress.com"}'), ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/01/07/rwa-job-losses/", "blog_url": "http://researchremix.wordpress.com"}')]
        assert_equals(response, expected)

    @http
    def test_aliases(self):
        response = self.provider.aliases([self.testitem_aliases])
        print response
        expected = [('url', 'http://researchremix.wordpress.com'), ('wordpress_blog_id', "1015265")] 
        assert_equals(response, expected)

    @http
    def test_metrics_wordpress_com_api_key_whole_blog(self):
        analytics_credentials = {"wordpress_api_key": self.api_key}
        metrics_dict = self.provider.metrics([self.testitem_metrics], analytics_credentials=analytics_credentials)
        print metrics_dict
        expected = {'wordpresscom:views': (75558, 'http://researchremix.wordpress.com'), 'wordpresscom:subscribers': (66, 'http://researchremix.wordpress.com')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_wordpress_com_wordpress_id_whole_blog(self):
        test_aliases = [('blog', 'http://researchremix.wordpress.com'), ('wordpress_blog_id', "1015265")] 
        metrics_dict = self.provider.metrics(test_aliases)
        print metrics_dict
        expected = {'wordpresscom:comments': (638, 'http://researchremix.wordpress.com'), 'wordpresscom:subscribers': (66, 'http://researchremix.wordpress.com')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]


    @http
    def test_metrics_wordpress_com_api_key_one_post(self):
        analytics_credentials = {"wordpress_api_key": self.api_key}
        wordpress_post_alias = ('wordpress_blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "researchremix.wordpress.com", "wordpress_post_id": 1119}')
        metrics_dict = self.provider.metrics([wordpress_post_alias], analytics_credentials=analytics_credentials)
        print metrics_dict
        expected = {'wordpresscom:comments': (13, None), 'wordpresscom:views': (1863, None)}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]


    @http
    def test_metrics_wordpress_com_without_api_key(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'wordpresscom:subscribers': (66, u'http://researchremix.wordpress.com')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_metrics_not_wordpress_com(self):
        metrics_dict = self.provider.metrics([("blog", "http://jasonpriem.com")])
        print metrics_dict
        expected = {}
        assert_equals(metrics_dict, expected)

    @http
    def test_biblio_wordpress_com(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'account': 'researchremix.wordpress.com', 'hosting_platform': 'wordpress.com', 'description': u'Blogging about the science, engineering, and human factors of biomedical research data reuse', 'title': u'Research Remix', 'url': 'http://researchremix.wordpress.com', 'is_account': True}
        assert_items_equal(biblio_dict.keys(), expected.keys())

    @http
    def test_biblio_not_wordpress_com(self):
        biblio_dict = self.provider.biblio([("blog", "http://jasonpriem.com")])
        print biblio_dict
        expected = {'url': 'http://jasonpriem.com', 'account': 'jasonpriem.com', 'is_account': True}
        assert_items_equal(biblio_dict.keys(), expected.keys())


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

    def test_provider_biblio_400(self):
        pass
    def test_provider_biblio_500(self):
        pass
