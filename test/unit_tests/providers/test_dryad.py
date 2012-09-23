from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from test.utils import http
from totalimpact.providers.provider import Provider, ProviderItemNotFoundError

import os
from nose.tools import assert_equals, raises
import collections

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/dryad")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

TEST_DRYAD_DOI = "10.5061/dryad.7898"
TEST_DRYAD_AUTHOR = "Piwowar, Heather A."
TEST_ALIASES_SEED = {"doi" : [TEST_DRYAD_DOI], "url" : ["http://datadryad.org/handle/10255/dryad.7898"]}

class TestDryad(ProviderTestCase):

    provider_name = "dryad"

    testitem_members = TEST_DRYAD_AUTHOR
    testitem_aliases = ("doi", TEST_DRYAD_DOI)
    testitem_metrics = ("doi", TEST_DRYAD_DOI)
    testitem_biblio = ("doi", TEST_DRYAD_DOI)
    testitem_provenance_url = "http://dx.doi.org/10.5061/dryad.7898"


    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate TEST_DRYAD_DOI
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)
        # ensure that it doesn't match an inappropriate TEST_DRYAD_DOI
        assert_equals(self.provider.is_relevant_alias(("doi", "11.12354/NOTDRYADDOI")), False)
    
    def test_extract_members(self):
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r")
        members = self.provider._extract_members(f.read(), TEST_DRYAD_AUTHOR)
        assert len(members) == 4, str(members)
        assert_equals(members, [('doi', u'10.5061/dryad.j1fd7'), ('doi', u'10.5061/dryad.mf1sd'), ('doi', u'10.5061/dryad.3td2f'), ('doi', u'10.5061/dryad.j2c4g')])

    @raises(ProviderItemNotFoundError)
    def test_extract_members_zero_items(self):
        page = """<?xml version="1.0" encoding="UTF-8"?>
                <response>
                <lst name="responseHeader"><int name="status">0</int><int name="QTime">0</int><lst name="params"><str name="fl">dc.identifier</str><str name="q">dc.contributor.author:"Piwowar, Heather A."</str></lst></lst><result name="response" numFound="0" start="0"></result>
                </response>"""
        members = self.provider._extract_members(page, TEST_DRYAD_AUTHOR)

    def test_extract_aliases(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_PAGE, "r")
        aliases = self.provider._extract_aliases(f.read())
        assert_equals(aliases, [('url', u'http://hdl.handle.net/10255/dryad.7898'), 
            ('title', u'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides')])        

    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        assert_equals(ret, {'authors': u'Ally, Ritland, Otto', 'year': u'2010', 'repository': 'Dryad Digital Repository', 'title': u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides'})

    def test_extract_stats(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(len(metrics_dict), 2)
        assert_equals(metrics_dict['dryad:package_views'], 149)
        assert_equals(metrics_dict['dryad:total_downloads'], 169)

    def test_extract_stats_invalid_id(self):
        # If the item has a DOI alias but it's not recognised by dryad, 
        #    then won't find any metrics. Should get a None returned.
        metrics = self.provider.metrics([("doi", "10.9999/NOTADRYADDOI")])
        assert_equals(metrics, {})

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        expected = {'dryad:package_views': (361, 'http://dx.doi.org/10.5061/dryad.7898'), 
            'dryad:total_downloads': (176, 'http://dx.doi.org/10.5061/dryad.7898')}
        print metrics_dict            
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

