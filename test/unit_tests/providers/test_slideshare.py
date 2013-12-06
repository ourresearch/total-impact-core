from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest, assert_true

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/slideshare")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

TEST_URL = "http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916"
TEST_URL2 = "www.slideshare.net/hpiwowar/right-time-right-place-to-change-the-world"
TEST_SLIDESHARE_USER = "cavlec"

class TestSlideshare(ProviderTestCase):

    provider_name = "slideshare"

    testitem_members = "cavlec"
    testitem_aliases = ("url", TEST_URL)
    testitem_metrics = ("url", TEST_URL)
    testitem_biblio = ("url", TEST_URL)

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    def test_extract_members(self):
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
        members = self.provider._extract_members(f.read(), TEST_SLIDESHARE_USER)
        assert_equals(len(members), 36)
        assert_true('url', u'http://www.slideshare.net/cavlec/avoiding-heronway' in members)

    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        assert_equals(ret, {'username': u'cavlec', 'title': u'Manufacturing Serendipity', 'repository': 'Slideshare', 'created': u'Tue Mar 27 10:10:11 -0500 2012'})

    def test_extract_aliases(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = self.provider._extract_aliases(f.read())
        assert_equals(aliases, [('title', u'Manufacturing Serendipity')])

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(metrics_dict["slideshare:views"], 337)
        assert_equals(metrics_dict["slideshare:downloads"], 4)

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'slideshare:downloads': (4, 'http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916'), 'slideshare:views': (543, 'http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916'), 'slideshare:favorites': (2, 'http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916')}
        print metrics_dict
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_provider_import(self):
        test_tabs = {"account_name": "cavlec", "standard_urls_input": TEST_URL2}
        members = provider.import_products("slideshare", test_tabs)
        print members
        expected = [('url', u'https://www.slideshare.net/hpiwowar/right-time-right-place-to-change-the-world'), ('url', u'http://www.slideshare.net/cavlec/week8-5557551'), ('url', u'http://www.slideshare.net/cavlec/canoe-the-open-content-rapids'), ('url', u'http://www.slideshare.net/cavlec/so-you-think-you-know-libraries'), ('url', u'http://www.slideshare.net/cavlec/what-we-organize'), ('url', u'http://www.slideshare.net/cavlec/escapar-la-carrera-de-la-reina'), ('url', u'http://www.slideshare.net/cavlec/librarians-love-data'), ('url', u'http://www.slideshare.net/cavlec/even-the-loons-are-licensed'), ('url', u'http://www.slideshare.net/cavlec/institutional-repositories-rebirth-of-the-phoenix'), ('url', u'http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916'), ('url', u'http://www.slideshare.net/cavlec/canoe-the-open-content-rapids-2862487'), ('url', u'http://www.slideshare.net/cavlec/encryption-27779361'), ('url', u'http://www.slideshare.net/cavlec/who-owns-our-work-notes'), ('url', u'http://www.slideshare.net/cavlec/rdf-rda-and-other-tlas'), ('url', u'http://www.slideshare.net/cavlec/whats-driving-open-access'), ('url', u'http://www.slideshare.net/cavlec/manufacturing-serendipity'), ('url', u'http://www.slideshare.net/cavlec/i-own-copyright-so-i-pwn-you'), ('url', u'http://www.slideshare.net/cavlec/paying-forit'), ('url', u'http://www.slideshare.net/cavlec/grab-a-bucket-its-raining-data'), ('url', u'http://www.slideshare.net/cavlec/soylent-semantic-web-is-people-with-notes'), ('url', u'http://www.slideshare.net/cavlec/who-owns-our-work'), ('url', u'http://www.slideshare.net/cavlec/soylent-semanticweb-is-people'), ('url', u'http://www.slideshare.net/cavlec/open-sesame-and-other-open-movements'), ('url', u'http://www.slideshare.net/cavlec/digital-preservation-and-institutional-repositories'), ('url', u'http://www.slideshare.net/cavlec/a-successful-failure-community-requirements-gathering-for-dspace'), ('url', u'http://www.slideshare.net/cavlec/project-management-16606291'), ('url', u'http://www.slideshare.net/cavlec/databases-markup-and-regular-expressions'), ('url', u'http://www.slideshare.net/cavlec/solving-problems-with-web-20'), ('url', u'http://www.slideshare.net/cavlec/educators-together'), ('url', u'http://www.slideshare.net/cavlec/le-ir-cest-mort-vive-le-ir'), ('url', u'http://www.slideshare.net/cavlec/open-content'), ('url', u'http://www.slideshare.net/cavlec/so-are-we-winning-yet'), ('url', u'http://www.slideshare.net/cavlec/save-the-cows-data-curation-for-the-rest-of-us-1533252'), ('url', u'http://www.slideshare.net/cavlec/grab-a-bucket-its-raining-data-2134106'), ('url', u'http://www.slideshare.net/cavlec/nsa-27779364'), ('url', u'http://www.slideshare.net/cavlec/is-this-big-data-which-i-see-before-me'), ('url', u'http://www.slideshare.net/cavlec/escaping-the-red-queens-race-with-open-access'), ('url', u'http://www.slideshare.net/cavlec/research-data-and-scholarly-communication'), ('url', u'http://www.slideshare.net/cavlec/so-arewewinningyet-notes'), ('url', u'http://www.slideshare.net/cavlec/week13-5972690'), ('url', u'http://www.slideshare.net/cavlec/privacy-inlibs'), ('url', u'http://www.slideshare.net/cavlec/marc-and-bibframe-linking-libraries-and-archives'), ('url', u'http://www.slideshare.net/cavlec/frbr-and-rda'), ('url', u'http://www.slideshare.net/cavlec/the-social-journal'), ('url', u'http://www.slideshare.net/cavlec/occupy-copyright'), ('url', u'http://www.slideshare.net/cavlec/research-data-and-scholarly-communication-16366049'), ('url', u'http://www.slideshare.net/cavlec/what-youre-up-against'), ('url', u'http://www.slideshare.net/cavlec/escaping-datageddon'), ('url', u'http://www.slideshare.net/cavlec/risk-management-and-auditing'), ('url', u'http://www.slideshare.net/cavlec/the-canonically-bad-digital-humanities-proposal'), ('url', u'http://www.slideshare.net/cavlec/data-and-the-law'), ('url', u'http://www.slideshare.net/cavlec/ejournals-and-open-access'), ('url', u'http://www.slideshare.net/cavlec/preservation-and-institutional-repositories-for-the-digital-arts-and-humanities'), ('url', u'http://www.slideshare.net/cavlec/avoiding-heronway'), ('url', u'http://www.slideshare.net/cavlec/taming-the-monster-digital-preservation-planning-and-implementation-tools'), ('url', u'http://www.slideshare.net/cavlec/library-linked-data')]
        for member in expected:
            assert(member in members)

