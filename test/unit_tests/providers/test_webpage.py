 # -*- coding: utf-8 -*-  # need this line because test utf-8 strings later

import os
import collections

from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from test.utils import slow, http

from nose.tools import assert_equals, raises

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/webpage")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

class TestWebpage(ProviderTestCase):

    provider_name = "webpage"

    testitem_aliases = ("url", "http://nescent.org")
    testitem_biblio = ("url", "http://nescent.org")
    testitem_members = "http://nescent.org\nhttp://blenz.ca\nhttps://heroku.com"

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A GITHUB ID")), False)
  
    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        expected = {'h1': u'WELCOME', 'title': u'NESCent: The National Evolutionary Synthesis Center'}
        assert_equals(ret, expected)

    def test_extract_biblio_russian(self):
        #from http://www.youtube.com/watch?v=9xBmU0TPZC4
        page = """<html><head><title>День города. Донецк 2010 - YouTube</title></head>
                <body>
                <h1 id="watch-headline-title">
                День города. Донецк 2010
                </h1>
              </body></html>"""
        ret = self.provider._extract_biblio(page)
        expected = {'h1': u'День города. Донецк 2010', 'title': u"День города. Донецк 2010 - YouTube"} 
        assert_equals(ret, expected)

    # override common because does not raise errors, unlike most other providers
    def test_provider_biblio_400(self):
        Provider.http_get = common.get_400
        biblio = self.provider.biblio([self.testitem_biblio])
        assert_equals(biblio, {})

    # override comon because does not raise errors, unlike most other providers
    def test_provider_biblio_500(self):
        Provider.http_get = common.get_500
        biblio = self.provider.biblio([self.testitem_biblio])
        assert_equals(biblio, {})

    def test_member_items(self):
        ret = self.provider.member_items(self.testitem_members)
        expected = [('url', 'http://nescent.org'), ('url', 'http://blenz.ca'), ('url', 'https://heroku.com')]
        assert_equals(ret, expected)        

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
        
    @http
    def test_biblio(self):
        ret = self.provider.biblio([("url", "http://www.digitalhumanities.org/dhq/vol/2/1/000019/000019.html")])
        expected = {'title': u'DHQ: Digital Humanities Quarterly: As You Can See: Applying Visual Collaborative Filtering to Works of Art'}
        assert_equals(ret, expected)

