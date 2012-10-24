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
    
    def test_extract_stats(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        print metrics_dict
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

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'title': u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides', 'year': u'2010', 'repository': u'Dryad Digital Repository', 'authors_literal': u'Ally, Dilara; Ritland, Kermit; Otto, Sarah P.'}
        assert_equals(biblio_dict, expected)

    @http
    def test_alias(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('biblio', {'title': u'Data from: Can clone size serve as a proxy for clone age? An exploration using microsatellite divergence in Populus tremuloides', 'year': u'2010', 'repository': u'Dryad Digital Repository', 'authors_literal': u'Ally, Dilara; Ritland, Kermit; Otto, Sarah P.'}), ('url', u'http://datadryad.org/handle/10255/dryad.7898'), ('url', 'http://dx.doi.org/10.5061/dryad.7898')]
        assert_equals(sorted(aliases), sorted(expected))

