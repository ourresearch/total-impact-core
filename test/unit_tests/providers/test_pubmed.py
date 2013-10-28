from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from test.utils import http
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/pubmed")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_FROM_DOI_PAGE = os.path.join(datadir, "aliases_from_doi")
SAMPLE_EXTRACT_ALIASES_FROM_PMID_PAGE = os.path.join(datadir, "aliases_from_pmid")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE

TEST_DOI = "10.1371/journal.pcbi.1000361"
TEST_PMID = "16060722"
TEST_DOI_HAS_NO_PMID = "10.1016/j.artint.2005.10.007"

class TestPubmed(ProviderTestCase):

    provider_name = "pubmed"

    testitem_aliases = ("pmid", TEST_PMID)
    testitem_biblio = ("pmid", TEST_PMID)
    testitem_metrics = ("pmid", TEST_PMID)
    testitem_members = "123\n456\n789"

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    def test_extract_aliases_from_doi(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_FROM_DOI_PAGE, "r")
        aliases = self.provider._extract_aliases_from_doi(f.read(), "10.1371/journal.pcbi.1000361")
        print aliases
        assert_equals(aliases, [('pmid', '19381256')])

    def test_extract_aliases_from_pmid(self):
        # ensure that the dryad reader can interpret an xml doc appropriately
        f = open(SAMPLE_EXTRACT_ALIASES_FROM_PMID_PAGE, "r")
        aliases = self.provider._extract_aliases_from_pmid(f.read(), "17593900")
        print aliases
        expected = [('doi', u'10.1371/journal.pmed.0040215'), ('url', u'http://dx.doi.org/10.1371/journal.pmed.0040215')]
        assert_equals(aliases, expected)

    # override default because returns url even if pmid api page is empty
    def test_provider_aliases_empty(self):
        Provider.http_get = common.get_empty
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        assert_equals(aliases, [("url", 'http://www.ncbi.nlm.nih.gov/pubmed/16060722')])

    def test_extract_citing_pmcids(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        pmcids = self.provider._extract_citing_pmcids(f.read())
        assert_equals(len(pmcids), 149)

    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio(f.read())
        expected = {'authors': u'Ioannidis', 'date': '2005-08-30T00:00:00', 'journal': u'PLoS medicine', 'year': "2005", 'title': u'Why most published research findings are false.'}
        assert_equals(ret, expected)

    def test_member_items(self):
        ret = self.provider.member_items(self.testitem_members)
        expected = [('pmid', '123'), ('pmid', '456'), ('pmid', '789')]
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
        biblio_dict = self.provider.biblio([self.testitem_biblio])
        expected = {'authors': u'Ioannidis', 'date': '2005-08-30T00:00:00', 'journal': u'PLoS medicine', 'year': "2005", 'title': u'Why most published research findings are false.'}
        assert_equals(biblio_dict, expected)

    @http
    def test_aliases_from_pmid(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('biblio', {'title': u'Why most published research findings are false.', 'journal': u'PLoS medicine', 'year': "2005", 'authors': u'Ioannidis', 'date': '2005-08-30T00:00:00'}), ('doi', u'10.1371/journal.pmed.0020124'), ('url', u'http://dx.doi.org/10.1371/journal.pmed.0020124'), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/16060722')]
        assert_equals(aliases, expected)

    @http
    def test_aliases_from_pmid_different_date_format(self):
        aliases = self.provider.aliases([("pmid", "11457506")])
        print aliases
        expected = [('biblio', {'title': u'Radiation hybrid mapping of 11 alpha and beta nicotinic acetylcholine receptor genes in Rattus norvegicus.', 'journal': u'Brain research. Molecular brain research', 'year': "2001", 'month': u'Jul', 'authors': u'Tseng, Kwitek-Black, Erbe, Popper, Jacob, Wackym', 'day': 13}), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/11457506')]
        assert_equals(aliases, expected)


    @http
    def test_aliases_from_pmid_when_doi_fragment(self):
        #this pmid has a partial doi in its doi field.  Make sure we don't include it in our doi field.
        aliases = self.provider.aliases([("pmid", "11244366")])
        print aliases
        expected = [('biblio', {'journal': u'ORL; journal for oto-rhino-laryngology and its related specialties', 'authors': u'Oshima, Ikeda, Furukawa, Suzuki, Takasaka', 'title': u'Expression of the voltage-dependent chloride channel ClC-3 in human nasal tissue.'}), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/11244366')]
        assert_equals(aliases, expected)

    @http
    def test_aliases_from_pmid_when_doi_in_different_part_of_xml(self):
        aliases = self.provider.aliases([("pmid", "23682040")])
        print aliases
        expected = [('biblio', {'title': u'Influenza: marketing vaccine by marketing disease.', 'journal': u'BMJ (Clinical research ed.)', 'year': "2013", 'authors': u'Doshi', 'date': '2013-05-16T00:00:00'}), ('doi', u'10.1136/bmj.f3037'), ('url', u'http://dx.doi.org/10.1136/bmj.f3037'), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/23682040')]
        assert_equals(aliases, expected)

    @http
    def test_aliases_from_doi(self):
        aliases_dict = self.provider.aliases([("doi", TEST_DOI)])
        assert_equals(set(aliases_dict), set([('pmid', '19381256')]))

        aliases_dict = self.provider.aliases([("doi", "TEST_DOI_HAS_NO_PMID")])
        assert_equals(aliases_dict, [])

    @http
    def test_metrics(self):
        metrics_dict = self.provider.metrics([self.testitem_metrics])
        print metrics_dict
        expected = {'pubmed:pmc_citations': (149, 'http://www.ncbi.nlm.nih.gov/pubmed?linkname=pubmed_pubmed_citedin&from_uid=16060722'), 'pubmed:f1000': (True, 'http://f1000.com/pubmed/16060722'), 'pubmed:pmc_citations_reviews': (20, 'http://www.ncbi.nlm.nih.gov/pubmed?term=22182676%20OR%2022065657%20OR%2021998558%20OR%2021890791%20OR%2021788505%20OR%2021407270%20OR%2020967426%20OR%2020637084%20OR%2020571517%20OR%2020420659%20OR%2020382258%20OR%2020307281%20OR%2019956635%20OR%2019860651%20OR%2019207020%20OR%2018834308%20OR%2018612135%20OR%2018603647%20OR%2017705840%20OR%2017587446&cmd=DetailsSearch'), 'pubmed:pmc_citations_editorials': (11, 'http://www.ncbi.nlm.nih.gov/pubmed?term=22515987%20OR%2022285994%20OR%2021693091%20OR%2021153562%20OR%2020876290%20OR%2020596038%20OR%2020420659%20OR%2020040241%20OR%2019967369%20OR%2019949717%20OR%2017880356&cmd=DetailsSearch')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]

            # the drilldown url changes with the metrics for some pubmed metrics, so don't check those
            if (key != "pubmed:pmc_citations_editorials") and (key != "pubmed:pmc_citations_reviews"):
                assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]

