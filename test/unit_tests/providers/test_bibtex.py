from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/bibtex")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "Lapp.bib")

class TestBibtex(ProviderTestCase):

    provider_name = "bibtex"

    testitem_members = "egonw"

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_extract_members_success(self):        
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
        members = self.provider.member_items(f.read())
        assert_equals(set(members), set([('doi', u'10.1091/mbc.E05-01-0062'), ('doi', u'10.1016/S0076-6879(05)03001-6'), ('doi', u'10.1007/s00335-005-0145-5'), ('doi', u'10.1101/gr.361602'), ('doi', u'10.1111/j.2041-210X.2010.00023.x'), ('doi', u'10.1186/2041-1480-1-8'), ('doi', u'10.1073/pnas.0400782101'), ('doi', u'10.1371/journal.pone.0010500'), ('doi', u'10.1093/icb/icr047'), ('doi', u'10.1371/journal.pone.0010708'), ('doi', u'10.1101/gr.2161804'), ('doi', u'10.1093/sysbio/syq013'), ('doi', u'10.1093/bib/bbl026'), ('doi', u'10.1111/j.1439-0426.2012.01985.x'), ('doi', u'10.1002/bult.2011.1720370411')]))

    def test_paginate(self):
        file_contents = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r").read()
        response = self.provider.paginate(file_contents)
        assert_equals(len(response), 3)
