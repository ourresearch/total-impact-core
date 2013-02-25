from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderServerError

import os, json
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/bibtex")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "Priem.bib")
with open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r") as f:
  SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS = f.read()

SAMPLE_PARSED_MEMBER_ITEMS_CONTENTS = [{'title': 'Scientometrics 2.0: New metrics of scholarly impact on the social Web', 'first_author': 'Priem', 'journal': 'First Monday', 'number': '7', 'volume': '15', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': '2010'}, {'title': 'Data for free: Using LMS activity logs to measure community in online courses', 'first_author': 'Black', 'journal': 'The Internet and Higher Education', 'number': '2', 'volume': '11', 'first_page': '65', 'authors': 'Black, Dawson, Priem', 'year': '2008'}, {'title': 'How and why scholars cite on Twitter', 'first_author': 'Priem', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '47', 'first_page': '1', 'authors': 'Priem, Costello', 'year': '2010'}, {'title': 'Archiving scholars\xe2\x80\x99 tweets', 'first_author': 'COSTELLO', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'COSTELLO, PRIEM', 'year': ''}, {'title': 'Altmetrics in the wild: An exploratory study of impact metrics based on social media', 'first_author': 'Priem', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Piwowar, Hemminger', 'year': ''}, {'title': 'Frontiers: Decoupling the scholarly journal', 'first_author': 'Priem', 'journal': 'Frontiers in Computational Neuroscience', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': ''}, {'title': 'FAIL BETTER: TOWARD A TAXONOMY OF E-LEARNING ERROR', 'first_author': 'PRIEM', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'PRIEM', 'year': ''}, {'title': 'Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': 'Garnett, Holmberg, Pikas, Piwowar, Priem, Weber', 'year': '2011'}, {'title': 'Shaken and stirred: ASIST 2011 attendee reactions to Shaking it up: embracing new methods for publishing, finding, discussing, and measuring our research output', 'first_author': 'Garnett', 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '48', 'first_page': '1', 'authors': 'Garnett, Piwowar, Holmberg, Priem, Pikas, Weber', 'year': '2011'}, {'title': 'Altmetrics: a manifesto', 'first_author': 'Priem', 'journal': '', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Taraborelli, Groth, Neylon', 'year': '2010'}, {'title': 'Altmetrics in the wild: Using social media to explore scholarly impact', 'first_author': 'Priem', 'journal': 'arXiv preprint arXiv:1203.4745', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Priem, Piwowar, Hemminger', 'year': '2012'}, {'title': 'Uncovering impacts: a case study in using altmetrics tools', 'first_author': 'Priem', 'journal': 'Workshop on the Semantic Publishing (SePublica 2012) 9 th Extended Semantic Web Conference Hersonissos, Crete, Greece, May 28, 2012', 'number': '', 'volume': '', 'first_page': '40', 'authors': 'Priem, Parra, Piwowar, Groth, Waagmeester', 'year': '2012'}, {'title': "Beyond citations: Scholars' visibility on the social Web", 'first_author': 'Bar-Ilan', 'journal': 'arXiv preprint arXiv:1205.5611', 'number': '', 'volume': '', 'first_page': '', 'authors': 'Bar-Ilan, Haustein, Peters, Priem, Shema, Terliesner', 'year': '2012'}, {'title': 'The Altmetrics Collection', 'first_author': 'Priem', 'journal': 'PloS one', 'number': '11', 'volume': '7', 'first_page': 'e48753', 'authors': 'Priem, Groth, Taraborelli', 'year': '2012'}, {'title': 'Information visualization state of the art and future directions', 'first_author': "Milojevi{\\'c}", 'journal': 'Proceedings of the American Society for Information Science and Technology', 'number': '1', 'volume': '49', 'first_page': '1', 'authors': "Milojevi{\\'c}, Hemminger, Priem, Chen, Leydesdorff, Weingart", 'year': '2012'}]

SAMPLE_EXTRACT_MEMBER_ITEMS_BROKEN = """
@999{test1,
  year={2009},
},
@article{test2,
  year={2009},
  test={no closing
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
}"""



class TestBibtex(ProviderTestCase):

    provider_name = "bibtex"
    testitem_members = "egonw"

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_extract_members_success(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        parsed = self.provider.parse(file_contents)

        members = self.provider.member_items(json.dumps(parsed))
        print members
        expected = [('biblio', {u'title': u'Scientometrics 2.0: New metrics of scholarly impact on the social Web', u'first_author': u'Priem', u'journal': u'First Monday', u'number': u'7', u'volume': u'15', u'first_page': u'', u'authors': u'Priem, Hemminger', u'year': u'2010'})]
        assert_equals(members[0], expected[0])
        
    def test_parse_none(self):
        file_contents = ""
        response = self.provider.parse(file_contents)
        assert_equals(len(response), 0)

    def test_parse_short(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT
        response = self.provider.parse(file_contents)
        print response
        assert_equals(len(response), 3)

    def test_parse_long(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        response = self.provider.parse(file_contents)

        # make sure it's json-serializable
        json_str = json.dumps(response)
        assert_equals(json_str[0:3], '[{"')

        assert_equals(len(response), 15) # 15 total articles
        print response
        assert_equals(response, SAMPLE_PARSED_MEMBER_ITEMS_CONTENTS)

    def test_lookup_dois_from_biblio(self):
        biblio_list = [
            {"first_author": "Piwowar", "journal": "PLoS medicine", "number": "9", "volume": "5", "first_page": "e183", "key": "piwowar2008towards", "year": "2008"},
            {"first_author": "Piwowar", "journal": "PLoS One", "number": "3", "volume": "2", "first_page": "e308", "key": "piwowar2007sharing", "year": "2007"}
        ]
        dois = self.provider._lookup_dois_from_biblio(biblio_list, True)
        assert_equals(set(dois), set([u'10.1371/journal.pmed.0050183',
                                      u'10.1371/journal.pone.0000308']))

    # check it doesn't throw an error
    def test_paginate_broken(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_BROKEN
        response = self.provider.parse(file_contents)
        #print 1/0


