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

    def test_extract_members_success(self):        
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        query_response = self.provider.paginate(file_contents)
        members = self.provider.member_items(query_response["pages"][1])
        print members
        expected = [('doi', u'10.1093/bioinformatics/btm001'), ('doi', u'10.1104/pp.103.023085'), ('doi', u'10.1093/bioinformatics/btg1008'), ('doi', u'10.1186/1471-2148-8-95')]
        assert_equals(set(members), set(expected))

    def test_extract_members_none(self):        
        members = self.provider.member_items([])
        assert_equals(members, [])

    @raises(ProviderServerError)
    def test_extract_members_500(self):        
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        Provider.http_get = common.get_500
        query_response = self.provider.paginate(file_contents)
        members = self.provider.member_items(query_response["pages"][0])

    def test_extract_members_empty(self):        
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        Provider.http_get = common.get_empty
        query_response = self.provider.paginate(file_contents)
        members = self.provider.member_items(query_response["pages"][0])
        assert_equals(members, [])

    def test_paginate_none(self):
        file_contents = ""
        response = self.provider.paginate(file_contents)
        assert_equals(len(response["pages"]), 0)
        assert_equals(response["number_entries"], 0)

    def test_paginate_short(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT
        response = self.provider.paginate(file_contents)
        assert_equals(set(response.keys()), set(['number_entries', 'pages']))
        assert_equals(len(response["pages"]), 1)
        assert_equals(response["number_entries"], 3)

    def test_paginate_long(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        response = self.provider.paginate(file_contents)
        assert_equals(set(response.keys()), set(['number_entries', 'pages']))
        assert_equals(len(response["pages"]), 16)
        assert_equals(response["number_entries"], 79)

    def test_parse_long(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_CONTENTS
        resp = self.provider.parse(file_contents)

        json_str = json.dumps(resp)
        assert_equals(json_str[0:3], '[{"') # just make sure it's json-serializable
        assert_equals(len(resp), 54) # 54 usable articles


    # check it doesn't throw an error
    def test_paginate_broken(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_BROKEN
        response = self.provider.paginate(file_contents)
        #print 1/0

