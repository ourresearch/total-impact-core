from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from test.utils import http
from totalimpact.providers.provider import Provider, ProviderItemNotFoundError

import os
from nose.tools import assert_equals, raises, nottest
import collections

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/orcid")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")

TEST_ORCID_ID = "0000-0003-1613-5981"

class TestOrcid(ProviderTestCase):

    provider_name = "orcid"

    testitem_members = TEST_ORCID_ID

    def setUp(self):
        ProviderTestCase.setUp(self)
    
    def test_extract_members(self):
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
        members = self.provider._extract_members(f.read(), TEST_ORCID_ID)
        print members
        expected = [('doi', '10.1002/meet.14504701413'), ('doi', '10.1038/npre.2007.425.2'), ('doi', '10.1002/meet.14504701421'), ('doi', '10.1038/npre.2008.2152.1'), ('doi', '10.1038/npre.2007.361'), ('doi', '10.1038/473285a'), ('doi', '10.1038/npre.2010.4267.1'), ('doi', '10.1016/j.joi.2009.11.010'), ('doi', '10.1038/npre.2010.5452.1')]
        assert_equals(members, expected)

    def test_extract_members_zero_items(self):
        page = """{"message-version":"1.0.6","orcid-profile":{"orcid":{"value":"0000-0003-1613-5981"}}}"""
        members = self.provider._extract_members(page, TEST_ORCID_ID)
        assert_equals(members, [])

    @http
    def test_member_items(self):
        members = self.provider.member_items(TEST_ORCID_ID)
        print members
        expected = [('doi', '10.1002/meet.14504701413'), ('doi', '10.1038/npre.2007.425.2'), ('doi', '10.1002/meet.14504701421'), ('doi', '10.1038/npre.2008.2152.1'), ('doi', '10.1038/npre.2007.361'), ('doi', '10.1038/473285a'), ('doi', '10.1038/npre.2010.4267.1'), ('doi', '10.1016/j.joi.2009.11.010'), ('doi', '10.1038/npre.2010.5452.1')]
        assert len(members) >= len(expected), str(members)

    @http
    def test_member_items_missing_dois(self):
        members = self.provider.member_items("0000-0001-5109-3700")  #another.  some don't have dois
        print members
        expected = [('doi', u'10.1087/20120404'), ('doi', u'10.1093/scipol/scs030'), ('doi', u'10.1126/science.caredit.a1200080'), ('doi', u'10.1016/S0896-6273(02)01067-X'), ('doi', u'10.1111/j.1469-7793.2000.t01-2-00019.xm'), ('doi', u'10.1046/j.0022-3042.2001.00727.x'), ('doi', u'10.1097/ACM.0b013e31826d726b'), ('doi', u'10.1126/science.1221840'), ('doi', u'10.1016/j.brainresbull.2006.08.006'), ('doi', u'10.1016/0006-8993(91)91536-A'), ('doi', u'10.1076/jhin.11.1.70.9111'), ('doi', u'10.2139/ssrn.1677993')]
        assert len(members) >= len(expected), str(members)


