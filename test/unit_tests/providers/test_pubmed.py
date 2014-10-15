from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from test.utils import http
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact import app, db
from totalimpact.providers import provider
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/pubmed")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_ALIASES_FROM_DOI_PAGE = os.path.join(datadir, "aliases_from_doi")
SAMPLE_EXTRACT_ALIASES_FROM_PMID_PAGE = os.path.join(datadir, "aliases_from_pmid")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_BIBLIO_ELINK_PAGE = os.path.join(datadir, "biblio_elink")
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
        self.db = setup_postgres_for_unittests(db, app)
        ProviderTestCase.setUp(self)
        
    def tearDown(self):
        teardown_postgres_for_unittests(self.db)

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
        expected = [('doi', u'10.1371/journal.pmed.0040215'), ('url', u'http://dx.doi.org/10.1371/journal.pmed.0040215'), ('pmc', u'PMC1896210'), ('url', u'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1896210')]
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

    def test_extract_biblio_efetch(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        ret = self.provider._extract_biblio_efetch(f.read())
        print ret
        expected = {'title': u'Why most published research findings are false.', 'journal': u'PLoS medicine', 'issn': u'15491676', 'authors': u'Ioannidis', 'keywords': u'Bias (Epidemiology); Data Interpretation, Statistical; Likelihood Functions; Meta-Analysis as Topic; Odds Ratio; Publishing; Reproducibility of Results; Research Design; Sample Size', 'year': '2005', 'date': '2005-08-30T00:00:00', 'abstract': u'There is increasing concern that most current published research findings are false. The probability that a research claim is true may depend on study power and bias, the number of other studies on the same question, and, importantly, the ratio of true to no relationships among the relationships probed in each scientific field. In this framework, a research finding is less likely to be true when the studies conducted in a field are smaller; when effect sizes are smaller; when there is a greater number and lesser preselection of tested relationships; where there is greater flexibility in designs, definitions, outcomes, and analytical modes; when there is greater financial and other interest and prejudice; and when more teams are involved in a scientific field in chase of statistical significance. Simulations show that for most study designs and settings, it is more likely for a research claim to be false than true. Moreover, for many current scientific fields, claimed research findings may often be simply accurate measures of the prevailing bias. In this essay, I discuss the implications of these problems for the conduct and interpretation of research.'}
        assert_equals(ret, expected)

    def test_extract_biblio_elink(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_ELINK_PAGE, "r")
        ret = self.provider._extract_biblio_elink(f.read())
        print ret
        expected = {'free_fulltext_url': 'http://www.nejm.org/doi/abs/10.1056/NEJMp1314561?url_ver=Z39.88-2003&rfr_id=ori:rid:crossref.org&rfr_dat=cr_pub%3dwww.ncbi.nlm.nih.gov'}
        assert_equals(ret, expected)

    def test_member_items(self):
        ret = self.provider.member_items(self.testitem_members)
        print ret
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
        print biblio_dict
        expected = {'title': u'Why most published research findings are false.', 'free_fulltext_url': 'http://dx.plos.org/10.1371/journal.pmed.0020124', 'journal': u'PLoS medicine', 'issn': u'15491676', 'year': '2005', 'keywords': u'Bias (Epidemiology); Data Interpretation, Statistical; Likelihood Functions; Meta-Analysis as Topic; Odds Ratio; Publishing; Reproducibility of Results; Research Design; Sample Size', 'authors': u'Ioannidis', 'date': '2005-08-30T00:00:00', 'abstract': u'There is increasing concern that most current published research findings are false. The probability that a research claim is true may depend on study power and bias, the number of other studies on the same question, and, importantly, the ratio of true to no relationships among the relationships probed in each scientific field. In this framework, a research finding is less likely to be true when the studies conducted in a field are smaller; when effect sizes are smaller; when there is a greater number and lesser preselection of tested relationships; where there is greater flexibility in designs, definitions, outcomes, and analytical modes; when there is greater financial and other interest and prejudice; and when more teams are involved in a scientific field in chase of statistical significance. Simulations show that for most study designs and settings, it is more likely for a research claim to be false than true. Moreover, for many current scientific fields, claimed research findings may often be simply accurate measures of the prevailing bias. In this essay, I discuss the implications of these problems for the conduct and interpretation of research.'}
        assert_equals(biblio_dict, expected)

    @http
    def test_biblio_free_full_text(self):
        biblio_dict = self.provider.biblio([("pmid", "24251383")])
        print biblio_dict
        expected = {'authors': u'Collins, Hamburg', 'keywords': u'Device Approval; Genome, Human; Humans; Individualized Medicine; Pharmacogenetics; Sequence Analysis, DNA; United States; United States Food and Drug Administration', 'title': u'First FDA authorization for next-generation sequencer.', 'date': '2013-11-19T00:00:00', 'free_fulltext_url': 'http://www.nejm.org/doi/abs/10.1056/NEJMp1314561?url_ver=Z39.88-2003&rfr_id=ori:rid:crossref.org&rfr_dat=cr_pub%3dwww.ncbi.nlm.nih.gov', 'journal': u'The New England journal of medicine', 'issn': u'15334406', 'year': '2013'}
        assert_equals(biblio_dict, expected)        

    @http
    def test_biblio_no_free_full_text(self):
        biblio_dict = self.provider.biblio([("pmid", "20150669")])
        print biblio_dict
        expected =  {'authors': u'R\xfcbel, Weber, Huang, Bethel, Biggin, Fowlkes, Luengo Hendriks, Ker\xe4nen, Eisen, Knowles, Malik, Hagen, Hamann', 'keywords': u'Chromosome Mapping; Computer Graphics; Computer Simulation; Database Management Systems; Databases, Genetic; Gene Expression Profiling; Models, Genetic; Multigene Family; Systems Integration; User-Computer Interface', 'title': u'Integrating data clustering and visualization for the analysis of 3D gene expression data.', 'journal': u'IEEE/ACM transactions on computational biology and bioinformatics / IEEE, ACM', 'issn': u'15579964', 'abstract': u'The recent development of methods for extracting precise measurements of spatial gene expression patterns from three-dimensional (3D) image data opens the way for new analyses of the complex gene regulatory networks controlling animal development. We present an integrated visualization and analysis framework that supports user-guided data clustering to aid exploration of these new complex data sets. The interplay of data visualization and clustering-based data classification leads to improved visualization and enables a more detailed analysis than previously possible. We discuss 1) the integration of data clustering and visualization into one framework, 2) the application of data clustering to 3D gene expression data, 3) the evaluation of the number of clusters k in the context of 3D gene expression clustering, and 4) the improvement of overall analysis quality via dedicated postprocessing of clustering results based on visualization. We discuss the use of this framework to objectively define spatial pattern boundaries and temporal profiles of genes and to analyze how mRNA patterns are controlled by their regulatory transcription factors.'}
        assert_equals(biblio_dict, expected)        

    @http
    def test_aliases_from_pmid(self):
        aliases = self.provider.aliases([self.testitem_aliases])
        print aliases
        expected = [('biblio', {'title': u'Why most published research findings are false.', 'journal': u'PLoS medicine', 'issn': u'15491676', 'authors': u'Ioannidis', 'keywords': u'Bias (Epidemiology); Data Interpretation, Statistical; Likelihood Functions; Meta-Analysis as Topic; Odds Ratio; Publishing; Reproducibility of Results; Research Design; Sample Size', 'year': '2005', 'date': '2005-08-30T00:00:00', 'abstract': u'There is increasing concern that most current published research findings are false. The probability that a research claim is true may depend on study power and bias, the number of other studies on the same question, and, importantly, the ratio of true to no relationships among the relationships probed in each scientific field. In this framework, a research finding is less likely to be true when the studies conducted in a field are smaller; when effect sizes are smaller; when there is a greater number and lesser preselection of tested relationships; where there is greater flexibility in designs, definitions, outcomes, and analytical modes; when there is greater financial and other interest and prejudice; and when more teams are involved in a scientific field in chase of statistical significance. Simulations show that for most study designs and settings, it is more likely for a research claim to be false than true. Moreover, for many current scientific fields, claimed research findings may often be simply accurate measures of the prevailing bias. In this essay, I discuss the implications of these problems for the conduct and interpretation of research.'}), ('doi', u'10.1371/journal.pmed.0020124'), ('pmc', u'PMC1182327'), ('url', u'http://dx.doi.org/10.1371/journal.pmed.0020124'), ('url', u'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1182327'), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/16060722')]
        assert_equals(aliases, expected)

    @http
    def test_aliases_from_pmid_when_pubmed_misses_doi(self):
        aliases = self.provider.aliases([("pmid", "18189011")])
        print aliases
        expected = ('doi', u'10.3758/CABN.7.4.380')
        assert expected in aliases

    @http
    def test_aliases_from_pmid_different_date_format(self):
        aliases = self.provider.aliases([("pmid", "11457506")])
        print aliases
        expected = [('biblio', {'title': u'Radiation hybrid mapping of 11 alpha and beta nicotinic acetylcholine receptor genes in Rattus norvegicus.', 'journal': u'Brain research. Molecular brain research', 'issn': u'0169328X', 'month': u'Jul', 'authors': u'Tseng, Kwitek-Black, Erbe, Popper, Jacob, Wackym', 'keywords': u'Animals; Cell Line; Cricetinae; DNA Primers; Efferent Pathways; Gene Expression; Molecular Sequence Data; Radiation Hybrid Mapping; Rats; Receptors, Nicotinic; Vestibular Nerve; Vestibule, Labyrinth', 'year': '2001', 'abstract': u'Acetylcholine is the main neurotransmitter of the vestibular efferents and a wide variety of muscarinic and nicotinic acetylcholine receptors are expressed in the vestibular periphery. To date, 11 nicotinic subunits (alpha and beta) have been reported in mammals. Previously, our group [Brain Res. 778 (1997) 409] reported that these nicotinic acetylcholine receptor alpha and beta subunits were differentially expressed in the vestibular periphery of the rat. To begin an understanding of the molecular genetics of these vestibular efferents, this study examined the chromosomal locations of these nicotinic acetylcholine receptor genes in the rat (Rattus norvegicus). Using radiation hybrid mapping and a rat radiation hybrid map server (www.rgd.mcw.edu/RHMAP SERVER/), we determined the chromosomal position for each of these genes. The alpha2-7, alpha9, alpha10, and beta2-4 nicotinic subunits mapped to the following chromosomes: alpha2, chr. 15; alpha3, chr. 8; alpha4, chr. 3; alpha5, chr. 8; alpha6, chr. 16; alpha7, chr. 1; alpha9, chr. 14; alpha10, chr. 7; beta2, chr. 2; beta3, chr. 16; and beta4, chr. 8. With the location for each of these nicotinic subunits known, it is now possible to develop consomic and/or congenic strains of rats that can be used to study the functional genomics of each of these subunits.', 'day': 13}), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/11457506')]
        assert_equals(aliases, expected)


    @http
    def test_aliases_from_pmid_when_doi_fragment(self):
        #this pmid has a partial doi in its doi field.  Make sure we don't include it in our doi field.
        aliases = self.provider.aliases([("pmid", "11244366")])
        print aliases
        expected = [('biblio', {'title': u'Expression of the voltage-dependent chloride channel ClC-3 in human nasal tissue.', 'journal': u'ORL; journal for oto-rhino-laryngology and its related specialties', 'issn': u'03011569', 'keywords': u'Chloride Channels; Humans; Immunohistochemistry; In Situ Hybridization; Nasal Mucosa; Reverse Transcriptase Polymerase Chain Reaction', 'authors': u'Oshima, Ikeda, Furukawa, Suzuki, Takasaka', 'abstract': u'In the present study, ClC-3, one of the voltage-dependent chloride channels, was identified in human nasal tissue. In situ hybridization and immunohistochemical investigations demonstrated the localization of ClC-3 in the serous acini and ductal portions of submucosal nasal glands, which are the primary source of nasal secretion. Our data suggest that this channel contributes to nasal secretion via chloride transport. Its dysfunction might lead to abnormal nasal secretion in such pathological states as sinusitis.'}), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/11244366')]
        assert_equals(aliases, expected)

    @http
    def test_aliases_from_pmid_when_doi_in_different_part_of_xml(self):
        aliases = self.provider.aliases([("pmid", "23682040")])
        print aliases
        expected = [('biblio', {'title': u'Influenza: marketing vaccine by marketing disease.', 'journal': u'BMJ (Clinical research ed.)', 'issn': u'17561833', 'authors': u'Doshi', 'keywords': u'Health Policy; Humans; Influenza Vaccines; Influenza, Human; Marketing of Health Services; Mass Vaccination; United States', 'year': '2013', 'date': '2013-05-16T00:00:00'}), ('doi', u'10.1136/bmj.f3037'), ('url', u'http://dx.doi.org/10.1136/bmj.f3037'), ('url', 'http://www.ncbi.nlm.nih.gov/pubmed/23682040')]
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

    @http
    def test_metrics_with_dup_pmids(self):
        metrics_dict = self.provider.metrics([("pmid", "22198174")])
        print metrics_dict
        expected = {'pubmed:pmc_citations': (6, 'http://www.ncbi.nlm.nih.gov/pubmed?linkname=pubmed_pubmed_citedin&from_uid=22198174'), 'pubmed:pmc_citations_reviews': (2, 'http://www.ncbi.nlm.nih.gov/pubmed?term=22886409%2520OR%252022732550&cmd=DetailsSearch')}
        for key in expected:
            assert metrics_dict[key][0] >= expected[key][0], [key, metrics_dict[key], expected[key]]

            # the drilldown url changes with the metrics for some pubmed metrics, so don't check those
            if (key != "pubmed:pmc_citations_editorials") and (key != "pubmed:pmc_citations_reviews"):
                assert metrics_dict[key][1] == expected[key][1], [key, metrics_dict[key], expected[key]]


