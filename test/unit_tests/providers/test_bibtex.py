from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderServerError

import os, json
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/bibtex")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "Vision.bib")
with open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r") as f:
  SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS = f.read()

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

    def test_extract_members_none(self):
        members = self.provider.member_items("[]")
        assert_equals(members, [])

    @raises(ProviderServerError)
    def test_extract_members_500(self):        
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        Provider.http_get = common.get_500
        parsed = self.provider.parse(file_contents)
        members = self.provider.member_items(json.dumps(parsed))

    def test_extract_members_empty(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        Provider.http_get = common.get_empty
        parsed = self.provider.parse(file_contents)
        members = self.provider.member_items(json.dumps(parsed))
        assert_equals(members, [])

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
        resp = self.provider.parse(file_contents)

        # make sure it's json-serializable
        json_str = json.dumps(resp)
        assert_equals(json_str[0:3], '[{"')

        assert_equals(len(resp), 79) # 79 total articles

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


