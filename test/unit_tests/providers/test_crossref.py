from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers import provider
from totalimpact import app, db
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

from test.utils import http

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/crossref")
SAMPLE_EXTRACT_ALIASES_PAGE = os.path.join(datadir, "aliases")
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")

TEST_DOI = "10.1371/journal.pcbi.1000361"

class TestCrossRef(ProviderTestCase):

    provider_name = "crossref"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_biblio = ("doi", TEST_DOI)
    testitem_members = "10.123/example\ndoi:10.456/example2\nhttp://doi.org/10.2342/example3"

    def setUp(self):
        ProviderTestCase.setUp(self)
        self.db = setup_postgres_for_unittests(db, app)
        
    def tearDown(self):
        teardown_postgres_for_unittests(self.db)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "NOT A CROSSREF ID")), False)
  
    def test_extract_biblio(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio = self.provider._extract_biblio(f.read())
        expected = {'title': 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'journal': 'PLoS Computational Biology', 'year': '2009', 'repository': 'Public Library of Science', 'authors': 'Shotton, Portwin, Klyne, Miles'}
        print biblio
        assert_equals(biblio, expected)

    def test_member_items(self):
        ret = self.provider.member_items(self.testitem_members)
        expected = [('doi', '10.123/example'), ('doi', '10.456/example2'), ('doi', '10.2342/example3')]
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
    def test_get_aliases_for_id(self):
        self.db = setup_postgres_for_unittests(db, app)
        new_aliases = self.provider.aliases([self.testitem_aliases])
        print new_aliases
        expected = [('biblio', {'issn': u'15537358', 'repository': u'Public Library of Science (PLoS)', 'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'journal': u'PLoS Computational Biology', 'year': '2009', 'free_fulltext_url': 'http://dx.doi.org/10.1371/journal.pcbi.1000361', 'authors': u'Shotton, Portwin, Klyne, Miles'}), ('url', 'http://dx.doi.org/10.1371/journal.pcbi.1000361'), ('url', u'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361')]
        assert_equals(sorted(new_aliases), sorted(expected))

    @http
    def test_biblio_elife(self):
        biblio = self.provider.biblio([("doi", "10.7554/eLife.00048")])
        expected = {'issn': u'2050084X', 'repository': u'eLife Sciences Publications, Ltd.', 'title': u'The unfolded protein response in fission yeast modulates stability of select mRNAs to maintain protein homeostasis', 'journal': u'eLife', 'year': '2012', 'authors': u'Kimmig, Diaz, Zheng, Williams, Lang, Aragon, Li, Walter'}

        print biblio
        assert_equals(biblio, expected)        

    @http
    def test_biblio_dryad(self):
        biblio = self.provider.biblio([("doi", "10.5061/dryad.3td2f")])
        expected = {'title': u'Data from: Public sharing of research datasets: a pilot study of associations', 'year': u'2011', 'repository': u'Dryad Digital Repository', 'authors_literal': u'Piwowar, Heather A.; Chapman, Wendy W.'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio_pangaea(self):
        biblio = self.provider.biblio([("doi", "10.1594/PANGAEA.339110")])
        expected = {'title': u"Audio record of a 'singing iceberg' from the Weddell Sea, Antarctica, supplement to: M\xfcller, Christian; Schlindwein, Vera; Eckstaller, Alfons; Miller, Heinz (2005): Singing Icebergs. Science, 310(5752), 1299", 'authors_literal': u'M\xfcller, Christian; Schlindwein, Vera; Eckstaller, Alfons; Miller, Heinz', 'repository': u'PANGAEA - Data Publisher for Earth & Environmental Science', 'year': '2005'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio_science(self):
        biblio = self.provider.biblio([("doi", "10.1126/science.169.3946.635")])
        expected = {'issn': u'00368075', 'repository': u'American Association for the Advancement of Science (AAAS)', 'title': u'The Structure of Ordinary Water: New data and interpretations are yielding new insights into this fascinating substance', 'journal': u'Science', 'year': '1970', 'authors': u'Frank'}
        print biblio
        assert_equals(biblio, expected) 

    @http
    def test_biblio(self):
        #setup_postgres_for_unittests(self.db, app)
        biblio = self.provider.biblio([self.testitem_biblio])
        expected = {'issn': u'15537358', 'repository': u'Public Library of Science (PLoS)', 'title': u'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'journal': u'PLoS Computational Biology', 'year': '2009', 'free_fulltext_url': 'http://dx.doi.org/10.1371/journal.pcbi.1000361', 'authors': u'Shotton, Portwin, Klyne, Miles'}
        print biblio
        assert_equals(biblio, expected)        

    @http
    def test_aliases_elife(self):
        aliases = self.provider.aliases([("doi", "10.7554/eLife.00048")])
        expected = [('biblio', {'issn': u'2050084X', 'repository': u'eLife Sciences Publications, Ltd.', 'title': u'The unfolded protein response in fission yeast modulates stability of select mRNAs to maintain protein homeostasis', 'journal': u'eLife', 'year': '2012', 'authors': u'Kimmig, Diaz, Zheng, Williams, Lang, Aragon, Li, Walter'}), ('url', 'http://dx.doi.org/10.7554/eLife.00048'), ('url', u'http://elife.elifesciences.org/content/1/e00048')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))

    @http
    def test_aliases_elife_table(self):
        aliases = self.provider.aliases([("doi", "10.7554/eLife.00048.020")])
        expected = [('biblio', {'repository': u'eLife Sciences Publications, Ltd.'}), ('url', 'http://dx.doi.org/10.7554/eLife.00048.020'), ('url', u'http://elife.elifesciences.org/content/1/e00048/T1')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))

    @http
    def test_aliases_from_url(self):
        aliases = self.provider.aliases([("url", "http://dx.doi.org/10.7554/eLife.00048.020")])
        expected = [('biblio', {'repository': u'eLife Sciences Publications, Ltd.'}), ('doi', '10.7554/eLife.00048.020'), ('url', 'http://dx.doi.org/10.7554/eLife.00048.020'), ('url', u'http://elife.elifesciences.org/content/1/e00048/T1')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))

    @http
    def test_aliases_bad_title(self):
        aliases = self.provider.aliases([("doi", "10.1021/np070361t")])
        expected = [('biblio', {'issn': u'01633864', 'repository': u'American Chemical Society (ACS)', 'title': u' 13 C\u2212 15 N Correlation via Unsymmetrical Indirect Covariance NMR: Application to Vinblastine ', 'journal': u'J. Nat. Prod.', 'year': '2007', 'authors': u'Martin, Hilton, Blinov, Williams'}), ('url', 'http://dx.doi.org/10.1021/np070361t'), ('url', u'http://pubs.acs.org/doi/abs/10.1021/np070361t')]
        print aliases
        assert_equals(sorted(aliases), sorted(expected))  

    @http
    def test_lookup_dois_from_biblio(self):
        biblio = {"first_author": "Piwowar", "journal": "PLoS medicine", "number": "9", "volume": "5", "first_page": "e183", "key": "piwowar2008towards", "year": "2008"}
        doi = self.provider._lookup_doi_from_biblio(biblio, True)
        assert_equals(doi, u'10.1371/journal.pmed.0050183')

    @http
    def test_aliases_from_biblio(self):
        biblio = {"first_author": "Piwowar", "journal": "PLoS medicine", "number": "9", "volume": "5", "first_page": "e183", "key": "piwowar2008towards", "year": "2008"}
        response = self.provider.aliases([("biblio", biblio)])
        print response
        expected = [('biblio', {'issn': u'15491277', 'repository': u'Public Library of Science (PLoS)', 'title': u'Towards a Data Sharing Culture: Recommendations for Leadership from Academic Health Centers', 'journal': u'Plos Med', 'year': '2008', 'authors': u'Piwowar, Becich, Bilofsky, Crowley'}), ('doi', u'10.1371/journal.pmed.0050183'), ('url', u'http://dx.doi.org/10.1371/journal.pmed.0050183'), ('url', u'http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0050183')]
        assert_equals(response, expected)

    @http
    def test_aliases_from_biblio2(self):
        biblio = {'title': 'Evaluating data citation and sharing policies in the environmental sciences', 'first_author': 'Weber', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Weber, Piwowar, Vision'}
        response = self.provider.aliases([("biblio", biblio)])
        print response
        expected = [('biblio', {'issn': u'00447870', 'repository': u'Wiley-Blackwell', 'title': u'Evaluating data citation and sharing policies in the environmental sciences', 'journal': u'Proc. Am. Soc. Info. Sci. Tech.', 'year': '2010', 'authors': u'Weber, Piwowar, Vision'}), ('doi', u'10.1002/meet.14504701445'), ('url', u'http://dx.doi.org/10.1002/meet.14504701445'), ('url', u'http://onlinelibrary.wiley.com/doi/10.1002/meet.14504701445/abstract')]
        assert_equals(response, expected)

    @http
    @raises(provider.ProviderServerError)
    def test_aliases_from_biblio3(self):
        biblio = {u'month': u'Dec', u'title': u'[Maternity in adolescence: obstetrical analysis and review of the influence of cultural, socioeconomic and psychological factors in a retrospective study of 62 cases].', u'year': 2002, u'authors': u'Faucher, Dappe, Madelenat', u'journal': u'Gyn\xe9cologie, obst\xe9trique & fertilit\xe9'}
        response = self.provider.aliases([("biblio", biblio)])
        print response
        expected = []
        assert_equals(response, expected)

    @http
    @nottest #so slow
    def test_aliases_from_biblio_multi(self):
        biblios = [{'title': 'Sharing detailed research data is associated with increased citation rate', 'first_author': 'Piwowar', 'journal': 'PLoS One', 'year': '2007', 'number': '3', 'volume': '2', 'first_page': 'e308', 'authors': 'Piwowar, Day, Fridsma'}, {'title': 'Towards a data sharing culture: recommendations for leadership from academic health centers', 'first_author': 'Piwowar', 'journal': 'PLoS medicine', 'year': '2008', 'number': '9', 'volume': '5', 'first_page': 'e183', 'authors': 'Piwowar, Becich, Bilofsky, Crowley'}, {'title': 'A review of journal policies for sharing research data', 'first_author': 'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Public sharing of research datasets: A pilot study of associations', 'first_author': 'Piwowar', 'journal': 'Journal of informetrics', 'year': '2010', 'number': '2', 'volume': '4', 'first_page': '148', 'authors': 'Piwowar, Chapman'}, {'title': 'Identifying data sharing in biomedical literature', 'first_author': 'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Recall and bias of retrieving gene expression microarray datasets through PubMed identifiers', 'first_author': 'Piwowar', 'journal': 'Journal of Biomedical Discovery and Collaboration', 'year': '2010', 'number': '', 'volume': '5', 'first_page': '7', 'authors': 'Piwowar, Chapman'}, {'title': 'Foundational studies for measuring the impact, prevalence, and patterns of publicly sharing biomedical research data', 'first_author': 'Piwowar', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar'}, {'title': 'Envisioning a biomedical data reuse registry.', 'first_author': 'Piwowar', 'journal': 'AMIA... Annual Symposium proceedings/AMIA Symposium. AMIA Symposium', 'year': '2008', 'number': '', 'volume': '', 'first_page': '1097', 'authors': 'Piwowar, Chapman'}, {'title': 'Using open access literature to guide full-text query formulation', 'first_author': 'Piwowar', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Linking database submissions to primary citations with PubMed Central', 'first_author': 'Piwowar', 'journal': 'BioLINK Workshop at ISMB', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Data archiving is a good investment', 'first_author': 'Piwowar', 'journal': 'Nature', 'year': '2011', 'number': '7347', 'volume': '473', 'first_page': '285', 'authors': 'Piwowar, Vision, Whitlock'}, {'title': 'Prevalence and patterns of microarray data sharing', 'first_author': 'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Formulating MEDLINE queries for article retrieval based on PubMed exemplars', 'first_author': 'Garnett', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Garnett, Piwowar, Rasmussen, Illes'}, {'title': "Who Shares? Who Doesn't? Factors Associated with Openly Archiving Raw Research Data", 'first_author': 'Piwowar', 'journal': 'PloS one', 'year': '2011', 'number': '7', 'volume': '6', 'first_page': 'e18657', 'authors': 'Piwowar'}, {'title': 'Examining the uses of shared data', 'first_author': 'Piwowar', 'journal': '', 'year': '2007', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Fridsma'}, {'title': 'Data from: Sharing detailed research data is associated with increased citation rate', 'first_author': 'Piwowar', 'journal': '', 'year': '2007', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Day, Fridsma'}, {'title': 'FOUNDATIONAL STUDIES FOR MEASURINGTHE IMPACT, PREVALENCE, AND PATTERNSOF PUBLICLY SHARING BIOMEDICAL RESEARCH DATA', 'first_author': 'Piwowar', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar'}, {'title': 'Biology needs a modern assessment system for professional productivity', 'first_author': 'McDade', 'journal': 'BioScience', 'year': '2011', 'number': '8', 'volume': '61', 'first_page': '619', 'authors': 'McDade, Maddison, Guralnick, Piwowar, Jameson, Helgen, Herendeen, Hill, Vis'}, {'title': 'Altmetrics in the wild: An exploratory study of impact metrics based on social media', 'first_author': 'Priem', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Piwowar, Hemminger'}, {'title': 'A method to track dataset reuse in biomedicine: filtered GEO accession numbers in PubMed Central', 'first_author': 'Piwowar', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Piwowar'}, {'title': 'Proposed Foundations for Evaluating Data Sharing and Reuse in the Biomedical Literature', 'first_author': 'Piwowar', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar'}, {'title': 'Data citation in the wild', 'first_author': 'Enriquez', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Enriquez, Judson, Walker, Allard, Cook, Piwowar, Sandusky, Vision, Wilson'}, {'title': 'Envisioning a data reuse registry', 'first_author': 'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Data from: Public sharing of research datasets: a pilot study of associations', 'first_author': 'Piwowar', 'journal': '', 'year': '2009', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Chapman'}, {'title': 'Uncovering impacts: CitedIn and total-impact, two new tools for gathering altmetrics.', 'first_author': 'Priem', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Parra, Waagmeester, Piwowar'}, {'title': "Who shares? Who doesn't? Bibliometric factors associated with open archiving of biomedical datasets", 'first_author': 'Piwowar', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Piwowar'}, {'title': 'PhD Thesis: Foundational studies for measuring the impact, prevalence, and patterns of publicly sharing biomedical research data', 'first_author': 'Piwowar', 'journal': 'Database', 'year': '2010', 'number': '3', 'volume': '25', 'first_page': '27', 'authors': 'Piwowar'}, {'title': 'Data from: Data archiving is a good investment', 'first_author': 'Piwowar', 'journal': '', 'year': '2011', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Vision, Whitlock'}, {'title': 'Expediting medical literature coding with query-building', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Garnett, Piwowar, Rasmussen, Illes'}, {'title': 'Neuroethics and fMRI: Mapping a Fledgling Relationship', 'first_author': 'Garnett', 'journal': 'PloS one', 'year': '2011', 'number': '4', 'volume': '6', 'first_page': 'e18537', 'authors': 'Garnett, Whiteley, Piwowar, Rasmussen, Illes'}, {'title': 'Beginning to track 1000 datasets from public repositories into the published literature', 'first_author': 'Piwowar', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar, Carlson, Vision'}, {'title': 'Evaluating data citation and sharing policies in the environmental sciences', 'first_author': 'Weber', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Weber, Piwowar, Vision'}, {'title': 'Data from: Who shares? Who doesn\xe2\x80\x99t? Factors associated with openly archiving raw research data', 'first_author': 'Piwowar', 'journal': '', 'year': '2011', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar'}, {'title': 'Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2011', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': 'Garnett, Holmberg, Pikas, Piwowar, Priem, Weber'}, {'title': 'Shaken and stirred: ASIST 2011 attendee reactions to Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'year': '2011', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': 'Garnett, Piwowar, Holmberg, Priem, Pikas, Weber'}, {'title': 'Altmetrics in the wild: Using social media to explore scholarly impact', 'first_author': 'Priem', 'journal': 'arXiv preprint arXiv:1203.4745', 'year': '2012', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Piwowar, Hemminger'}, {'title': 'Why Are There So Few Efforts to Text Mine the Open Access Subset of PubMed Central?', 'first_author': 'Piwowar', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar'}, {'title': 'Uncovering impacts: a case study in using altmetrics tools', 'first_author': 'Priem', 'journal': 'Workshop on the Semantic Publishing (SePublica 2012) 9 th Extended Semantic Web Conference Hersonissos, Crete, Greece, May 28, 2012', 'year': '2012', 'number': '', 'volume': '', 'first_page': '40', 'authors': 'Priem, Parra, Piwowar, Groth, Waagmeester'}, {'title': 'Uncovering the impact story of open research', 'first_author': 'Piwowar', 'journal': '', 'year': '2012', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Piwowar'}, {'title': 'Altmetrics: Value all research products', 'first_author': 'Piwowar', 'journal': 'Nature', 'year': '2013', 'number': '7431', 'volume': '493', 'first_page': '159', 'authors': 'Piwowar'}]
        responses = []
        for biblio in biblios:
            response = self.provider.aliases([("biblio", biblio)])
            print response
            responses += response
        print responses
        expected = [('biblio', {'repository': u'Public Library of Science', 'title': u'Sharing Detailed Research Data Is Associated with Increased Citation Rate', 'journal': u'PLoS ONE', 'year': '2007', 'authors': u'Piwowar, Day, Fridsma'}), ('doi', u'10.1371/journal.pone.0000308'), ('url', u'http://dx.doi.org/10.1371/journal.pone.0000308'), ('url', u'http://www.plosone.org/article/info%3Adoi%2F10.1371%2Fjournal.pone.0000308'), ('biblio', {'repository': u'Public Library of Science', 'title': u'Towards a Data Sharing Culture: Recommendations for Leadership from Academic Health Centers', 'journal': u'PLoS Medicine', 'year': '2008', 'authors': u'Piwowar, Becich, Bilofsky, Crowley'}), ('doi', u'10.1371/journal.pmed.0050183'), ('url', u'http://dx.doi.org/10.1371/journal.pmed.0050183'), ('url', u'http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0050183'), ('biblio', {'repository': u'Elsevier', 'title': u'Public sharing of research datasets: A pilot study of associations', 'journal': u'Journal of Informetrics', 'year': '2010', 'authors': u'Piwowar, Chapman'}), ('doi', u'10.1016/j.joi.2009.11.010'), ('url', u'http://dx.doi.org/10.1016/j.joi.2009.11.010'), ('url', u'http://www.sciencedirect.com/science/article/pii/S1751157709000881'), ('biblio', {'repository': u'Nature Publishing Group', 'title': u'Data archiving is a good investment', 'journal': u'Nature', 'year': '2011', 'authors': u'Piwowar, Vision, Whitlock'}), ('doi', u'10.1038/473285a'), ('url', u'http://dx.doi.org/10.1038/473285a'), ('biblio', {'repository': u'Public Library of Science', 'title': u"Who Shares? Who Doesn't? Factors Associated with Openly Archiving Raw Research Data", 'journal': u'PLoS ONE', 'year': '2011', 'authors': u'Piwowar'}), ('doi', u'10.1371/journal.pone.0018657'), ('url', u'http://dx.doi.org/10.1371/journal.pone.0018657'), ('url', u'http://www.plosone.org/article/info%3Adoi%2F10.1371%2Fjournal.pone.0018657'), ('biblio', {'repository': u'University of California Press', 'title': u'Biology Needs a Modern Assessment System for Professional Productivity', 'journal': u'BioScience', 'year': '2011', 'authors': u'McDade, Maddison, Guralnick, Piwowar, Jameson, Helgen, Herendeen, Hill, Vis'}), ('doi', u'10.1525/bio.2011.61.8.8'), ('url', u'http://dx.doi.org/10.1525/bio.2011.61.8.8'), ('url', u'http://www.jstor.org/discover/10.1525/bio.2011.61.8.8?uid=3739400&uid=2&uid=3737720&uid=4&sid=21101701097323'), ('biblio', {'repository': u'Wiley Blackwell (John Wiley & Sons)', 'title': u'Expediting medical literature coding with query-building', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'authors': u'Garnett, Piwowar, Rasmussen, Illes'}), ('doi', u'10.1002/meet.14504701421'), ('url', u'http://dx.doi.org/10.1002/meet.14504701421'), ('url', u'http://onlinelibrary.wiley.com/doi/10.1002/meet.14504701421/abstract'), ('biblio', {'repository': u'Public Library of Science', 'title': u'Neuroethics and fMRI: Mapping a Fledgling Relationship', 'journal': u'PLoS ONE', 'year': '2011', 'authors': u'Garnett, Whiteley, Piwowar, Rasmussen, Illes'}), ('doi', u'10.1371/journal.pone.0018537'), ('url', u'http://dx.doi.org/10.1371/journal.pone.0018537'), ('url', u'http://www.plosone.org/article/info%3Adoi%2F10.1371%2Fjournal.pone.0018537'), ('biblio', {'repository': u'Wiley Blackwell (John Wiley & Sons)', 'title': u'Evaluating data citation and sharing policies in the environmental sciences', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'authors': u'Weber, Piwowar, Vision'}), ('doi', u'10.1002/meet.14504701445'), ('url', u'http://dx.doi.org/10.1002/meet.14504701445'), ('url', u'http://onlinelibrary.wiley.com/doi/10.1002/meet.14504701445/abstract')]
        assert_equals(responses, expected)

