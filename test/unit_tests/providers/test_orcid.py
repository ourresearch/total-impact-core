from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from test.utils import http
from totalimpact.providers.provider import Provider, ProviderItemNotFoundError

import os
from nose.tools import assert_equals, raises, nottest
import collections

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/orcid")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "members")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE2 = os.path.join(datadir, "members2")

TEST_ORCID_ID = "0000-0003-1613-5981"
TEST_ORCID_ID2 = "0000-0001-9107-0714"
# test curl -H "Accept: application/orcid+json" htid.org/0000-0001-9107-0714/orcid-works

SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT = """
<orcid-work put-code="5177473">
                    <work-title>
                        <title>The Bioperl toolkit: Perl modules for the life sciences</title>
                        <subtitle>Genome Research</subtitle>
                    </work-title>
                    <work-citation>
                        <work-citation-type>bibtex</work-citation-type>
                        <citation>@article{lapp2002,
    volume  = {12},
    number  = {10},
    pages   = {1611-1618},
}
</citation>
                    </work-citation>
                    <publication-date>
                        <year>2002</year>
                    </publication-date>
                    <url>http://www.scopus.com/inward/record.url?eid=2-s2.0-18644368714&amp;partnerID=MN8TOARS</url>
                    <work-source>NOT_DEFINED</work-source>
                </orcid-work>
"""

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

    def test_extract_members(self):
        f = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE2, "r")
        members = self.provider._extract_members(f.read(), TEST_ORCID_ID2)
        print members
        expected = [('biblio', {'url': '', 'journal': '', 'title': 'The PLOS Computational Biology Software Section', 'year': '2012'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-84861306656&partnerID=MN8TOARS', 'journal': 'Journal of Applied Ichthyology', 'title': '500,000 fish phenotypes: The new informatics landscape for evolutionary and developmental biology of the vertebrate skeleton', 'year': '2012'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-84862498268&partnerID=MN8TOARS', 'journal': 'Systematic Biology', 'title': 'NeXML: Rich, extensible, and verifiable representation of comparative data and metadata', 'year': '2012'}), ('biblio', {'url': '', 'journal': '', 'title': 'Organizing our knowledge of biodiversity', 'year': '2011'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-79960529406&partnerID=MN8TOARS', 'journal': 'Integrative and Comparative Biology', 'title': 'Overview of FEED, the feeding experiments end-user database', 'year': '2011'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-84862168904&partnerID=MN8TOARS', 'journal': 'Database', 'title': 'The Chado Natural Diversity module: A new generic database schema for large-scale phenotyping and genotyping data', 'year': '2011'}), ('biblio', {'url': '', 'journal': '', 'title': 'The Teleost Taxonomy Ontology', 'year': '2010'}), ('biblio', {'url': '', 'journal': '', 'title': 'TreeBASE2: Rise of the Machines', 'year': '2010'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-77956229224&partnerID=MN8TOARS', 'journal': 'PLoS ONE', 'title': 'Evolutionary characters, phenotypes and ontologies: Curating data from the systematic biology literature', 'year': '2010'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-77956398373&partnerID=MN8TOARS', 'journal': 'PLoS ONE', 'title': 'Phenex: Ontological annotation of phenotypic diversity', 'year': '2010'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-77953795230&partnerID=MN8TOARS', 'journal': 'Systematic Biology', 'title': 'The teleost anatomy ontology: Anatomical representation for the genomics age', 'year': '2010'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-77955007716&partnerID=MN8TOARS', 'journal': 'Evolution', 'title': 'linking big: The continuing promise of evolutionary synthesis', 'year': '2010'}), ('biblio', {'url': '', 'journal': '', 'title': 'LINKING BIG: THE CONTINUING PROMISE OF EVOLUTIONARY SYNTHESIS', 'year': '2009'}), ('biblio', {'url': '', 'journal': '', 'title': 'Phenoscape: Ontologies for Large Multi-species Phenotype Datasets', 'year': '2009'}), ('biblio', {'url': '', 'journal': '', 'title': 'Comparative methods in R hackathon', 'year': '2008'}), ('biblio', {'url': 'http://www.la-press.com/the-2006-nescent-phyloinformatics-hackathon-a-field-report-article-a480', 'journal': '', 'title': 'The 2006 NESCent Phyloinformatics Hackathon: A Field Report', 'year': '2007'}), ('biblio', {'url': '', 'journal': '', 'title': 'Persistent BioPerl', 'year': '2007'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-33645513194&partnerID=MN8TOARS', 'journal': 'Mammalian Genome', 'title': 'Data and animal management software for large-scale phenotype screening', 'year': '2006'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-33748796893&partnerID=MN8TOARS', 'journal': 'Briefings in Bioinformatics', 'title': 'Open source tools and toolkits for bioinformatics: Significance, and where are we?', 'year': '2006'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-30544447301&partnerID=MN8TOARS', 'journal': 'Methods in Enzymology', 'title': 'Exploring trafficking GTPase function by mRNA expression profiling: Use of the SymAtlas web-application and the membrome datasets', 'year': '2005'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-23044472125&partnerID=MN8TOARS', 'journal': 'Molecular Biology of the Cell', 'title': 'Large-scale profiling of Rab GTPase trafficking networks: The membrome', 'year': '2005'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-11144358198&partnerID=MN8TOARS', 'journal': 'Proceedings of the National Academy of Sciences of the United States of America', 'title': 'A gene atlas of the mouse and human protein-encoding transcriptomes', 'year': '2004'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-12444303031&partnerID=MN8TOARS', 'journal': 'Genome Research', 'title': 'Applications of a rat multiple tissue gene expression data set', 'year': '2004'}), ('biblio', {'url': '', 'journal': '', 'title': 'Robust DNA microarray image analysis', 'year': '2003'}), ('biblio', {'url': '', 'journal': '', 'title': 'Automatic Grid Fitting for Genetic Spot Array Images Containing Guide Spots', 'year': '2003'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-11144277252&partnerID=MN8TOARS', 'journal': 'Machine Vision and Applications', 'title': 'Robust DNA microarray image analysis', 'year': '2003'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-18644368714&partnerID=MN8TOARS', 'journal': 'Genome Research', 'title': 'The Bioperl toolkit: Perl modules for the life sciences', 'year': '2002'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-0034878733&partnerID=MN8TOARS', 'journal': 'Proceedings of SPIE - The International Society for Optical Engineering', 'title': 'A generic and robust approach for the analysis of spot array images', 'year': '2001'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-0035887459&partnerID=MN8TOARS', 'journal': 'Cancer Research', 'title': 'Molecular classification of human carcinomas by use of gene expression signatures', 'year': '2001'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-0034564270&partnerID=MN8TOARS', 'journal': 'Proceedings / . International Conference on Intelligent Systems for Molecular Biology ; ISMB. International Conference on Intelligent Systems for Molecular Biology', 'title': 'Robust parametric and semi-parametric spot fitting for spot array images.', 'year': '2000'}), ('biblio', {'url': 'http://www.scopus.com/inward/record.url?eid=2-s2.0-0034444429&partnerID=MN8TOARS', 'journal': 'IEEE International Conference on Image Processing', 'title': 'Robust spot fitting for genetic spot array images', 'year': '2000'})]
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
    def test_member_items_some_missing_dois(self):
        members = self.provider.member_items("0000-0001-5109-3700")  #another.  some don't have dois
        print members
        expected = [('doi', u'10.1087/20120404'), ('doi', u'10.1093/scipol/scs030'), ('doi', u'10.1126/science.caredit.a1200080'), ('doi', u'10.1016/S0896-6273(02)01067-X'), ('doi', u'10.1111/j.1469-7793.2000.t01-2-00019.xm'), ('doi', u'10.1046/j.0022-3042.2001.00727.x'), ('doi', u'10.1097/ACM.0b013e31826d726b'), ('doi', u'10.1126/science.1221840'), ('doi', u'10.1016/j.brainresbull.2006.08.006'), ('doi', u'10.1016/0006-8993(91)91536-A'), ('doi', u'10.1076/jhin.11.1.70.9111'), ('doi', u'10.2139/ssrn.1677993')]
        assert len(members) >= len(expected), str(members)



