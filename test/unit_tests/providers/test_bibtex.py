from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderServerError


import os, json
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/bibtex")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "Priem.bib")
with open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r") as f:
  SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS = f.read()

SAMPLE_PARSED_MEMBER_ITEMS_CONTENTS = [{'title': 'Scientometrics 2.0: New metrics of scholarly impact on the social Web', 'first_author': 'Priem', 'journal': 'First Monday', 'number': '7', 'volume': '15', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': '2010'}, {'title': 'Data for free: Using LMS activity logs to measure community in online courses', 'first_author': 'Black', 'journal': 'The Internet and Higher Education', 'number': '2', 'volume': '11', 'first_page': '65', 'authors': 'Black, Dawson, Priem', 'year': '2008'}, {'title': 'How and why scholars cite on Twitter', 'first_author': 'Priem', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Priem, Costello', 'year': '2010'}, {'title': u'Archiving scholars\u2019 tweets', 'first_author': 'COSTELLO', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'COSTELLO, PRIEM', 'year': ''}, {'title': 'Altmetrics in the wild: An exploratory study of impact metrics based on social media', 'first_author': 'Priem', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Piwowar, Hemminger', 'year': ''}, {'title': 'Frontiers: Decoupling the scholarly journal', 'first_author': 'Priem', 'journal': 'Frontiers in Computational Neuroscience', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': ''}, {'title': 'FAIL BETTER: TOWARD A TAXONOMY OF E-LEARNING ERROR', 'first_author': 'PRIEM', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'PRIEM', 'year': ''}, {'title': 'Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': 'Garnett, Holmberg, Pikas, Piwowar, Priem, Weber', 'year': '2011'}, {'title': 'Shaken and stirred: ASIST 2011 attendee reactions to Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': 'Garnett, Piwowar, Holmberg, Priem, Pikas, Weber', 'year': '2011'}, {'title': 'Altmetrics: a manifesto', 'first_author': 'Priem', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Taraborelli, Groth, Neylon', 'year': '2010'}, {'title': 'Altmetrics in the wild: Using social media to explore scholarly impact', 'first_author': 'Priem', 'journal': 'arXiv preprint arXiv:1203.4745', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Piwowar, Hemminger', 'year': '2012'}, {'title': 'Uncovering impacts: a case study in using altmetrics tools', 'first_author': 'Priem', 'journal': 'Workshop on the Semantic Publishing (SePublica 2012) 9 th Extended Semantic Web Conference Hersonissos, Crete, Greece, May 28, 2012', 'number': '', 'volume': '', 'first_page': '40', 'authors': 'Priem, Parra, Piwowar, Groth, Waagmeester', 'year': '2012'}, {'title': "Beyond citations: Scholars' visibility on the social Web", 'first_author': 'Bar-Ilan', 'journal': 'arXiv preprint arXiv:1205.5611', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Bar-Ilan, Haustein, Peters, Priem, Shema, Terliesner', 'year': '2012'}, {'title': 'The Altmetrics Collection', 'first_author': 'Priem', 'journal': 'PloS one', 'number': '11', 'volume': '7', 'first_page': 'e48753', 'authors': 'Priem, Groth, Taraborelli', 'year': '2012'}, {'title': 'Information visualization state of the art and future directions', 'first_author': u'Milojevi\u0107', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '49', 'first_page': '1', 'authors': u'Milojevi\u0107, Hemminger, Priem, Chen, Leydesdorff, Weingart', 'year': '2012'}]

SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE2 = os.path.join(datadir, "Piwowar.bib")
with open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE2, "r") as f:
  SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS2 = f.read()

SAMPLE_EXTRACT_MEMBER_ITEMS_UNICODE = r"""
@article{oberg2003luftutslapp,
  title={Luftutsl{\"a}pp av organiska milj{\"o}gifter fr{\aa}n ljusb{\aa}gsugnar: F{\"o}rekomst och m{\"o}jliga {\aa}tg{\"a}rder f{\"o}r att minska milj{\"o}p{\aa}verkan},
  author={{\"O}berg, T.},
  year={2003},
  publisher={Jernkontoret,}
}
"""

SAMPLE_EXTRACT_MEMBER_ITEMS_BROKEN = """
@article{test1,
  year={2009},
},
@article{test2,
  year={2009},
  test={no closing
}
"""

SAMPLE_EXTRACT_MEMBER_ITEMS_ARXIV = """
@article{priem2012altmetrics,
  title={Altmetrics in the wild: Using social media to explore scholarly impact},
  author={Priem, J. and Piwowar, H.A. and Hemminger, B.M.},
  journal={arXiv preprint arXiv:1203.4745},
  year={2012}
}
"""

SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT = """
@phdthesis{rogers2006identity,
  title={Identity crisis| Modernity and fragmentation},
  author={Rogers, K.L.},
  year={2006},
  school={UNIVERSITY OF COLORADO AT BOULDER}
}

@article{rogers2008affirming,
  title={Affirming Complexity:" White Teeth" and Cosmopolitanism},
  author={Rogers, K.},
  journal={Interdisciplinary Literary Studies},
  volume={9},
  number={2},
  pages={45--61},
  year={2008},
  publisher={Penn State Altoona}
}

@phdthesis{rogers2010trauma,
  title={Trauma and the representation of the unsayable in late twentieth-century fiction},
  author={Rogers, K.L.},
  year={2010},
  school={UNIVERSITY OF COLORADO AT BOULDER}
}
"""



class TestBibtex(ProviderTestCase):

    provider_name = "bibtex"
    testitem_members = "egonw"

    def setUp(self):
        ProviderTestCase.setUp(self)
        
    def test_parse_none(self):
        file_contents = ""
        response = self.provider.parse(file_contents)
        assert_equals(len(response), 0)

    def test_parse_short(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT
        response = self.provider.parse(file_contents)
        print response
        assert_equals(len(response), 3)

    def test_paginate_unicode(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_UNICODE
        response = self.provider.parse(file_contents)
        print response
        expected = [{'title': u'Luftutsl\xe4pp av organiska milj\xf6gifter fr\xe5n ljusb\xe5gsugnar: F\xf6rekomst och m\xf6jliga \xe5tg\xe4rder f\xf6r att minska milj\xf6p\xe5verkan', 'first_author': u'\xd6berg', 'journal': '', 'year': '2003', 'number': '', 'volume': '', 'first_page': '', 'authors': u'\xd6berg'}]
        assert_equals(response, expected)

    def test_parse_long(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        response = self.provider.parse(file_contents)

        # make sure it's json-serializable
        json_str = json.dumps(response)
        assert_equals(json_str[0:3], '[{"')

        assert_equals(len(response), 15) # 15 total articles
        print response
        assert_equals(response, SAMPLE_PARSED_MEMBER_ITEMS_CONTENTS)


    def test_parse_long2(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS2
        response = self.provider.parse(file_contents)

        assert_equals(len(response), 40) # 40 total articles
        print response
        expected = [{'title': u'Sharing detailed research data is associated with increased citation rate', 'first_author': u'Piwowar', 'journal': u'PLoS One', 'year': '2007', 'number': '3', 'volume': '2', 'first_page': 'e308', 'authors': u'Piwowar, Day, Fridsma'}, {'title': u'Towards a data sharing culture: recommendations for leadership from academic health centers', 'first_author': u'Piwowar', 'journal': u'PLoS medicine', 'year': '2008', 'number': '9', 'volume': '5', 'first_page': 'e183', 'authors': u'Piwowar, Becich, Bilofsky, Crowley'}, {'title': u'A review of journal policies for sharing research data', 'first_author': u'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Public sharing of research datasets: A pilot study of associations', 'first_author': u'Piwowar', 'journal': u'Journal of informetrics', 'year': '2010', 'number': '2', 'volume': '4', 'first_page': '148', 'authors': u'Piwowar, Chapman'}, {'title': u'Identifying data sharing in biomedical literature', 'first_author': u'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Recall and bias of retrieving gene expression microarray datasets through PubMed identifiers', 'first_author': u'Piwowar', 'journal': u'Journal of Biomedical Discovery and Collaboration', 'year': '2010', 'number': '', 'volume': '5', 'first_page': '7', 'authors': u'Piwowar, Chapman'}, {'title': u'Foundational studies for measuring the impact, prevalence, and patterns of publicly sharing biomedical research data', 'first_author': u'Piwowar', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar'}, {'title': u'Envisioning a biomedical data reuse registry.', 'first_author': u'Piwowar', 'journal': u'AMIA... Annual Symposium proceedings/AMIA Symposium. AMIA Symposium', 'year': '2008', 'number': '', 'volume': '', 'first_page': '1097', 'authors': u'Piwowar, Chapman'}, {'title': u'Using open access literature to guide full-text query formulation', 'first_author': u'Piwowar', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Linking database submissions to primary citations with PubMed Central', 'first_author': u'Piwowar', 'journal': u'BioLINK Workshop at ISMB', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Data archiving is a good investment', 'first_author': u'Piwowar', 'journal': u'Nature', 'year': '2011', 'number': '7347', 'volume': '473', 'first_page': '285', 'authors': u'Piwowar, Vision, Whitlock'}, {'title': u'Prevalence and patterns of microarray data sharing', 'first_author': u'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Formulating MEDLINE queries for article retrieval based on PubMed exemplars', 'first_author': u'Garnett', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Garnett, Piwowar, Rasmussen, Illes'}, {'title': u"Who Shares? Who Doesn't? Factors Associated with Openly Archiving Raw Research Data", 'first_author': u'Piwowar', 'journal': u'PloS one', 'year': '2011', 'number': '7', 'volume': '6', 'first_page': 'e18657', 'authors': u'Piwowar'}, {'title': u'Examining the uses of shared data', 'first_author': u'Piwowar', 'journal': '', 'year': '2007', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Fridsma'}, {'title': u'Data from: Sharing detailed research data is associated with increased citation rate', 'first_author': u'Piwowar', 'journal': '', 'year': '2007', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Day, Fridsma'}, {'title': u'FOUNDATIONAL STUDIES FOR MEASURINGTHE IMPACT, PREVALENCE, AND PATTERNSOF PUBLICLY SHARING BIOMEDICAL RESEARCH DATA', 'first_author': u'Piwowar', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar'}, {'title': u'Biology needs a modern assessment system for professional productivity', 'first_author': u'McDade', 'journal': u'BioScience', 'year': '2011', 'number': '8', 'volume': '61', 'first_page': '619', 'authors': u'McDade, Maddison, Guralnick, Piwowar, Jameson, Helgen, Herendeen, Hill, Vis'}, {'title': u'Altmetrics in the wild: An exploratory study of impact metrics based on social media', 'first_author': u'Priem', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Priem, Piwowar, Hemminger'}, {'title': u'A method to track dataset reuse in biomedicine: filtered GEO accession numbers in PubMed Central', 'first_author': u'Piwowar', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': u'Piwowar'}, {'title': u'Proposed Foundations for Evaluating Data Sharing and Reuse in the Biomedical Literature', 'first_author': u'Piwowar', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar'}, {'title': u'Data citation in the wild', 'first_author': u'Enriquez', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Enriquez, Judson, Walker, Allard, Cook, Piwowar, Sandusky, Vision, Wilson'}, {'title': u'Envisioning a data reuse registry', 'first_author': u'Piwowar', 'journal': '', 'year': '2008', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Data from: Public sharing of research datasets: a pilot study of associations', 'first_author': u'Piwowar', 'journal': '', 'year': '2009', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Chapman'}, {'title': u'Uncovering impacts: CitedIn and total-impact, two new tools for gathering altmetrics.', 'first_author': u'Priem', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Priem, Parra, Waagmeester, Piwowar'}, {'title': u"Who shares? Who doesn't? Bibliometric factors associated with open archiving of biomedical datasets", 'first_author': u'Piwowar', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': u'Piwowar'}, {'title': u'PhD Thesis: Foundational studies for measuring the impact, prevalence, and patterns of publicly sharing biomedical research data', 'first_author': u'Piwowar', 'journal': u'Database', 'year': '2010', 'number': '3', 'volume': '25', 'first_page': '27', 'authors': u'Piwowar'}, {'title': u'Data from: Data archiving is a good investment', 'first_author': u'Piwowar', 'journal': '', 'year': '2011', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Vision, Whitlock'}, {'title': u'Expediting medical literature coding with query-building', 'first_author': u'Garnett', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': u'Garnett, Piwowar, Rasmussen, Illes'}, {'title': u'Neuroethics and fMRI: Mapping a Fledgling Relationship', 'first_author': u'Garnett', 'journal': u'PloS one', 'year': '2011', 'number': '4', 'volume': '6', 'first_page': 'e18537', 'authors': u'Garnett, Whiteley, Piwowar, Rasmussen, Illes'}, {'title': u'Beginning to track 1000 datasets from public repositories into the published literature', 'first_author': u'Piwowar', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar, Carlson, Vision'}, {'title': u'Evaluating data citation and sharing policies in the environmental sciences', 'first_author': u'Weber', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': u'Weber, Piwowar, Vision'}, {'title': u'Data from: Who shares? Who doesn\u2019t? Factors associated with openly archiving raw research data', 'first_author': u'Piwowar', 'journal': '', 'year': '2011', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar'}, {'title': u'Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': u'Garnett', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2011', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': u'Garnett, Holmberg, Pikas, Piwowar, Priem, Weber'}, {'title': u'Shaken and stirred: ASIST 2011 attendee reactions to Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': u'Garnett', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2011', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': u'Garnett, Piwowar, Holmberg, Priem, Pikas, Weber'}, {'title': u'Altmetrics in the wild: Using social media to explore scholarly impact', 'first_author': u'Priem', 'journal': u'arXiv preprint arXiv:1203.4745', 'year': '2012', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Priem, Piwowar, Hemminger'}, {'title': u'Why Are There So Few Efforts to Text Mine the Open Access Subset of PubMed Central?', 'first_author': u'Piwowar', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar'}, {'title': u'Uncovering impacts: a case study in using altmetrics tools', 'first_author': u'Priem', 'journal': u'Workshop on the Semantic Publishing (SePublica 2012) 9 th Extended Semantic Web Conference Hersonissos, Crete, Greece, May 28, 2012', 'year': '2012', 'number': '', 'volume': '', 'first_page': '40', 'authors': u'Priem, Parra, Piwowar, Groth, Waagmeester'}, {'title': u'Uncovering the impact story of open research', 'first_author': u'Piwowar', 'journal': '', 'year': '2012', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Piwowar'}, {'title': u'Altmetrics: Value all research products', 'first_author': u'Piwowar', 'journal': u'Nature', 'year': '2013', 'number': '7431', 'volume': '493', 'first_page': '159', 'authors': u'Piwowar'}]
        assert_equals(response, expected)

    # check it doesn't throw an error
    def test_paginate_broken(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_BROKEN
        response = self.provider.parse(file_contents)
        print response
        expected = [{'title': '', 'first_author': '', 'journal': '', 'year': '2009', 'number': '', 'volume': '', 'first_page': '', 'authors': ''}]
        assert_equals(response, expected)

    def test_member_items_arxiv(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_ARXIV
        response = self.provider.member_items(file_contents)
        print response
        expected = [('arxiv', u'1203.4745')]
        assert_equals(response, expected)

    def test_member_items(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        response = self.provider.member_items(file_contents)
        print response

        expected = [('biblio', {'title': u'Scientometrics 2.0: New metrics of scholarly impact on the social Web', 'first_author': u'Priem', 'journal': u'First Monday', 'year': '2010', 'number': '7', 'volume': '15', 'first_page': '', 'authors': u'Priem, Hemminger'}), ('biblio', {'title': u'Data for free: Using LMS activity logs to measure community in online courses', 'first_author': u'Black', 'journal': u'The Internet and Higher Education', 'year': '2008', 'number': '2', 'volume': '11', 'first_page': '65', 'authors': u'Black, Dawson, Priem'}), ('biblio', {'title': u'How and why scholars cite on Twitter', 'first_author': u'Priem', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2010', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': u'Priem, Costello'}), ('biblio', {'title': u'Archiving scholars\u2019 tweets', 'first_author': u'COSTELLO', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'COSTELLO, PRIEM'}), ('biblio', {'title': u'Altmetrics in the wild: An exploratory study of impact metrics based on social media', 'first_author': u'Priem', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Priem, Piwowar, Hemminger'}), ('biblio', {'title': u'Frontiers: Decoupling the scholarly journal', 'first_author': u'Priem', 'journal': u'Frontiers in Computational Neuroscience', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Priem, Hemminger'}), ('biblio', {'title': u'FAIL BETTER: TOWARD A TAXONOMY OF E-LEARNING ERROR', 'first_author': u'PRIEM', 'journal': '', 'year': '', 'number': '', 'volume': '', 'first_page': '', 'authors': u'PRIEM'}), ('biblio', {'title': u'Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': u'Garnett', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2011', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': u'Garnett, Holmberg, Pikas, Piwowar, Priem, Weber'}), ('biblio', {'title': u'Shaken and stirred: ASIST 2011 attendee reactions to Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': u'Garnett', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2011', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': u'Garnett, Piwowar, Holmberg, Priem, Pikas, Weber'}), ('biblio', {'title': u'Altmetrics: a manifesto', 'first_author': u'Priem', 'journal': '', 'year': '2010', 'number': '', 'volume': '', 'first_page': '', 'authors': u'Priem, Taraborelli, Groth, Neylon'}), ('arxiv', u'1203.4745'), ('biblio', {'title': u'Uncovering impacts: a case study in using altmetrics tools', 'first_author': u'Priem', 'journal': u'Workshop on the Semantic Publishing (SePublica 2012) 9 th Extended Semantic Web Conference Hersonissos, Crete, Greece, May 28, 2012', 'year': '2012', 'number': '', 'volume': '', 'first_page': '40', 'authors': u'Priem, Parra, Piwowar, Groth, Waagmeester'}), ('arxiv', u'1205.5611'), ('biblio', {'title': u'The Altmetrics Collection', 'first_author': u'Priem', 'journal': u'PloS one', 'year': '2012', 'number': '11', 'volume': '7', 'first_page': 'e48753', 'authors': u'Priem, Groth, Taraborelli'}), ('biblio', {'title': u'Information visualization state of the art and future directions', 'first_author': u'Milojevi\u0107', 'journal': u'Proceedings of the American Society for Information Science and Technology', 'year': '2012', 'number': '1', 'volume': '49', 'first_page': '1', 'authors': u'Milojevi\u0107, Hemminger, Priem, Chen, Leydesdorff, Weingart'})]
        assert_equals(response, expected)

