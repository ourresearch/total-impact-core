from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from test.utils import http

import os
import collections
from nose.tools import assert_equals, assert_items_equal, raises


class TestGithub_Account(ProviderTestCase):

    provider_name = "github_account"

    testitem_members = "egonw"
    testitem_aliases = ("url", "https://github.com/egonw")
    testitem_metrics = ("url", "https://github.com/egonw")
    testitem_biblio = ("url", "https://github.com/egonw")

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(("url", "https://github.com/egonw/cdk")), False)
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)
        assert_equals(self.provider.is_relevant_alias(("doi", "NOT A GITHUB ID")), False)
  
    # def test_provenance_url(self):
    #     provenance_url = self.provider.provenance_url("github:forks", [self.testitem_aliases])
    #     assert_equals(provenance_url, "https://github.com/egonw/cdk/network/members")

    #     # Not the same as above
    #     provenance_url = self.provider.provenance_url("github:stars", [self.testitem_aliases])
    #     assert_equals(provenance_url, "https://github.com/egonw/cdk/stargazers")

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'number_contributions': (819, 'https://github.com/egonw'), 'organizations': ('bioclipse, cdk, ToxBank, openphacts, molprops, JChemPaint, BiGCAT-UM, opentox-api, bridgedb, taverna', 'https://github.com/egonw'), 'github:languages': ([{u'count': 1715, u'quantile': 4, u'language': u'Java'}, {u'count': 106, u'quantile': 100, u'language': u'R'}, {u'count': 96, u'quantile': 100, u'language': u'JavaScript'}, {u'count': 61, u'quantile': 100, u'language': u'PHP'}, {u'count': 59, u'quantile': 100, u'language': u'TeX'}, {u'count': 33, u'quantile': 100, u'language': u'Groovy'}, {u'count': 13, u'quantile': 100, u'language': u'CSS'}, {u'count': 11, u'quantile': 100, u'language': u'DOT'}, {u'count': 10, u'quantile': 100, u'language': u'Scala'}, {u'count': 5, u'quantile': 100, u'language': u'Perl'}, {u'count': 3, u'quantile': 100, u'language': u'XSLT'}, {u'count': 1, u'quantile': 100, u'language': u'C++'}, {u'count': 1, u'quantile': 100, u'language': u'C'}], 'https://github.com/egonw'), 'longest_streak_days': (8, 'https://github.com/egonw'), 'github:number_gists': (183, 'https://github.com/egonw'), 'github:followers': (91, 'https://github.com/egonw'), 'github:number_repos': (118, 'https://github.com/egonw'), 'github:active_repos': ([{u'count': 496, u'repo': u'egonw/cdk'}, {u'count': 306, u'repo': u'cdk/cdk'}, {u'count': 164, u'repo': u'johnmay/cdk'}, {u'count': 91, u'repo': u'BiGCAT-UM/WikiPathwaysCurator'}, {u'count': 82, u'repo': u'egonw/rrdf'}], 'https://github.com/egonw'), 'github:joined_date': (u'2008-09-29T11:26:00Z', 'https://github.com/egonw')}
        assert_items_equal(expected.keys(), metrics_dict.keys())
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]
            assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

    @http
    def test_biblio(self):
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        print biblio_dict
        expected = {'genre': 'account', 'account': 'https://github.com/egonw', 'is_account': True, 'repository': 'GitHub'}
        assert_items_equal(biblio_dict.keys(), expected.keys())

    def test_provider_biblio_400(self):
        pass

    def test_provider_biblio_500(self):
        pass

    def test_provider_metrics_empty(self):
        pass

    def test_provider_metrics_nonsense_txt(self):
        pass

    def test_provider_metrics_nonsense_xml(self):
        pass
