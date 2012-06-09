from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os
import collections
from nose.tools import assert_equals, raises, nottest, assert_true

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/slideshare")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

TEST_URL = "http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916"
TEST_SLIDESHARE_USER = "cavlec"

class TestSlideshare(ProviderTestCase):

    provider_name = "slideshare"

    testitem_members = TEST_URL
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


