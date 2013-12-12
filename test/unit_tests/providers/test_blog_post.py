from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import http

import os
import collections
import json
from nose.tools import assert_equals, assert_items_equal, raises, nottest

class TestBlog_post(ProviderTestCase):

    provider_name = "blog_post"

    testitem_aliases = ('blog_post', json.dumps({"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "http://researchremix.wordpress.com"}))
    testitem_aliases_not_wordpress_com = ('blog_post', json.dumps({"post_url": "http://jasonpriem.org/2012/05/toward-a-second-revolution-altmetrics-total-impact-and-the-decoupled-journal-video/", "blog_url": "http://jasonpriem.org/blog"}))
    api_key = os.environ["WORDPRESS_OUR_BLOG_API_KEY"]

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("url", "https://twitter.com/researchremix/status/400821465828061184")), False)


    @http
    def test_aliases_wordpress_com(self):
        response = self.provider.aliases([self.testitem_aliases])
        print response
        expected = [('url', u'http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/'), ('wordpress_blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "http://researchremix.wordpress.com", "wordpress_post_id": 1119}')]
        assert_equals(response, expected)

    @http
    def test_aliases_not_wordpress(self):
        response = self.provider.aliases([('blog_post', json.dumps({"post_url": "http://jasonpriem.com/cv", "blog_url": "jasonpriem.com"}))])
        print response
        expected = [('url', u'http://jasonpriem.com/cv')]
        assert_equals(response, expected)


    @http
    def test_biblio_wordpress(self):
        response = self.provider.biblio([self.testitem_aliases])
        print response
        expected = {'url': u'http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/', 'account': u'researchremix.wordpress.com', 'hosting_platform': 'wordpress.com', 'blog_title': 'Research Remix', 'title': 'Elsevier agrees UBC researchers can text-mine for citizen science, research tools'}
        assert_equals(response, expected)

    @http
    def test_biblio_wordpress(self):
        response = self.provider.biblio([self.testitem_aliases])
        print response
        expected = {'url': u'http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/', 'account': u'researchremix.wordpress.com', 'hosting_platform': 'wordpress.com', 'blog_title': 'Research Remix', 'title': 'Elsevier agrees UBC researchers can text-mine for citizen science, research tools'}
        assert_equals(response, expected)

    @http
    def test_biblio_not_wordpress2(self):
        test_alias = ('blog_post', "{\"post_url\": \"http://researchremix.wordpress.com/2011/08/10/personal\", \"blog_url\": \"http://researchremix.wordpress.com\"}")
        response = self.provider.biblio([test_alias])
        print response
        expected = {'url': u'http://researchremix.wordpress.com/2011/08/10/personal', 'account': u'researchremix.wordpress.com', 'hosting_platform': 'wordpress.com', 'blog_title': 'Research Remix', 'title': 'Cancer data: it just got personal'}
        assert_equals(response, expected)

    @http
    @nottest
    def test_metrics(self):
        wordpress_aliases = [('url', u'http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/'), ('wordpress_blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "researchremix.wordpress.com", "wordpress_post_id": 1119}')]
        response = self.provider.metrics(wordpress_aliases)
        print response
        expected = {}
        assert_equals(response, expected)


    def test_provider_aliases_400(self):
        pass
    def test_provider_aliases_500(self):
        pass

    def test_provider_biblio_400(self):
        pass
    def test_provider_biblio_500(self):
        pass

    def test_provider_metrics_400(self):
        pass
    def test_provider_metrics_500(self):
        pass
    def test_provider_metrics_empty(self):
        pass
    def test_provider_metrics_nonsense_txt(self):
        pass
    def test_provider_metrics_nonsense_xml(self):
        pass