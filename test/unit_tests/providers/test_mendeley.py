from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderClientError, ProviderServerError
from totalimpact.providers import provider

from test.utils import http
from totalimpact import app, db
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests

import os
import collections
from nose.tools import assert_equals, raises, nottest


TEST_DOI = "10.1038/nature10658"  # matches UUID sample page

class TestMendeley(ProviderTestCase):

    provider_name = "mendeley"

    testitem_aliases = ("doi", TEST_DOI)
    testitem_aliases_biblio_no_doi =  ("biblio", {'title': 'Scientometrics 2.0: Toward new metrics of scholarly impact on the social Web', 'first_author': 'Priem', 'journal': 'First Monday', 'number': '7', 'volume': '15', 'first_page': '', 'authors': 'Priem, Hemminger', 'year': '2010'})
    testitem_metrics_dict = {"biblio":[{"year":2011, "authors":"sdf", "title": "Mutations causing syndromic autism define an axis of synaptic pathophysiology"}],"doi":[TEST_DOI]}
    testitem_metrics = [(k, v[0]) for (k, v) in testitem_metrics_dict.items()]
    testitem_metrics_dict_wrong_year = {"biblio":[{"year":9999, "authors":"sdf", "title": "Mutations causing syndromic autism define an axis of synaptic pathophysiology"}],"doi":[TEST_DOI]}
    testitem_metrics_wrong_year = [(k, v[0]) for (k, v) in testitem_metrics_dict_wrong_year.items()]

    def setUp(self):
        self.db = setup_postgres_for_unittests(db, app)
        ProviderTestCase.setUp(self)
        
    def tearDown(self):
        teardown_postgres_for_unittests(self.db)

    def test_is_relevant_alias(self):
        # ensure that it matches an appropriate ids
        assert_equals(self.provider.is_relevant_alias(self.testitem_aliases), True)

        assert_equals(self.provider.is_relevant_alias(("github", "egonw,cdk")), False)
  
    @http
    def test_metrics_doi(self):
        # at the moment this item 
        metrics_dict = self.provider.metrics([("doi", "10.1038/nature10658")])
        print metrics_dict
        expected = {'mendeley:discipline': ({u'Economics': 1, u'Psychology': 10, u'Business Administration': 1, u'Physics': 1, u'Philosophy': 2, u'Engineering': 1, u'Environmental Sciences': 1, u'Arts and Literature': 1, u'Biological Sciences': 229, u'Medicine': 44, u'Mathematics': 1, u'Computer and Information Science': 2, u'Social Sciences': 1}, u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology'), 'mendeley:countries': ({u'Canada': 2, u'United Kingdom': 5, u'Netherlands': 4, u'Portugal': 2, u'Mexico': 1, u'Finland': 1, u'France': 3, u'United States': 21, u'Austria': 2, u'Vietnam': 1, u'Germany': 4, u'China': 2, u'Japan': 4, u'Brazil': 5, u'New Zealand': 1, u'Spain': 1}, u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology'), 'mendeley:career_stage': ({u'Researcher (at a non-Academic Institution)': 7, u'Ph.D. Student': 79, u'Student (Bachelor)': 21, u'Student (Postgraduate)': 8, u'Professor': 19, u'Student (Master)': 20, u'Assistant Professor': 17, u'Other Professional': 15, u'Doctoral Student': 7, u'Associate Professor': 11, u'Lecturer': 2, u'Post Doc': 65, u'Researcher (at an Academic Institution)': 22, u'Senior Lecturer': 2}, u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology'), 'mendeley:readers': (295, u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology')}
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 

    @http
    def test_metrics_pmid(self):
        # at the moment this item 
        metrics_dict = self.provider.metrics([("pmid", "12578738")])
        expected = {'mendeley:discipline': ({u'Materials Science': 1, u'Business Administration': 4, u'Computer and Information Science': 5, u'Social Sciences': 3, u'Biological Sciences': 2}, u'http://www.mendeley.com/research/value-data-2'), 'mendeley:countries': ({u'United States': 1, u'Brazil': 1, u'Philippines': 1, u'Denmark': 1, u'Belgium': 1}, u'http://www.mendeley.com/research/value-data-2'), 'mendeley:career_stage': ({u'Ph.D. Student': 3, u'Student (Bachelor)': 1, u'Professor': 1, u'Assistant Professor': 1, u'Researcher (at an Academic Institution)': 1, u'Student (Master)': 7, u'Librarian': 1}, u'http://www.mendeley.com/research/value-data-2'), 'mendeley:readers': (15, u'http://www.mendeley.com/research/value-data-2')}
        print metrics_dict
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 
        # can't tell more about dicsciplines etc because they are percentages and may go up or down

    @http
    def test_metrics_arxiv(self):
        # at the moment this item 
        metrics = self.provider.metrics([("arxiv", "1203.4745")])
        print metrics
        expected = {'mendeley:discipline': ({u'Astronomy / Astrophysics / Space Science': 2, u'Materials Science': 1, u'Sports and Recreation': 1, u'Psychology': 4, u'Chemistry': 1, u'Business Administration': 3, u'Physics': 2, u'Management Science / Operations Research': 1, u'Earth Sciences': 4, u'Humanities': 10, u'Engineering': 1, u'Environmental Sciences': 4, u'Arts and Literature': 2, u'Biological Sciences': 13, u'Medicine': 16, u'Mathematics': 1, u'Philosophy': 1, u'Education': 13, u'Computer and Information Science': 70, u'Social Sciences': 47, u'Electrical and Electronic Engineering': 1}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley:countries': ({'FR': 2, 'DK': 2, 'DE': 12, 'JP': 4, 'BR': 9, 'FI': 1, 'NL': 6, 'PT': 1, 'MY': 1, 'LT': 1, 'VE': 1, 'CA': 9, 'IT': 4, 'ZA': 4, 'AR': 1, 'AU': 3, 'GB': 17, 'IE': 1, 'ES': 7, 'UA': 1, 'US': 27, 'SG': 1, 'MX': 1, 'SE': 2, 'AT': 1}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley:career_stage': ({u'Researcher (at a non-Academic Institution)': 5, u'Ph.D. Student': 30, u'Student (Bachelor)': 6, u'Student (Postgraduate)': 7, u'Professor': 8, u'Student (Master)': 16, u'Lecturer': 2, u'Assistant Professor': 5, u'Other Professional': 24, u'Doctoral Student': 4, u'Associate Professor': 9, u'Librarian': 48, u'Post Doc': 11, u'Researcher (at an Academic Institution)': 21, u'Senior Lecturer': 2}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley:readers': (198, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact')}
        assert_equals(metrics, expected)

    @http
    def test_metrics_title(self):
        # at the moment this item 
        alias = (u'biblio', {u'title': u'Altmetrics in the wild: Using social media to explore scholarly impact', u'first_author': u'Priem', u'journal': u'arXiv preprint arXiv:1203.4745', u'authors': u'Priem, Piwowar, Hemminger', u'number': u'', u'volume': u'', u'first_page': u'', u'year': u'2012'})
        metrics = self.provider.metrics([alias])
        print metrics
        expected = {'mendeley:discipline': ({u'Astronomy / Astrophysics / Space Science': 2, u'Materials Science': 1, u'Sports and Recreation': 1, u'Psychology': 4, u'Chemistry': 1, u'Business Administration': 3, u'Physics': 2, u'Management Science / Operations Research': 1, u'Earth Sciences': 4, u'Humanities': 10, u'Engineering': 1, u'Environmental Sciences': 4, u'Arts and Literature': 2, u'Biological Sciences': 13, u'Medicine': 16, u'Mathematics': 1, u'Philosophy': 1, u'Education': 13, u'Computer and Information Science': 70, u'Social Sciences': 47, u'Electrical and Electronic Engineering': 1}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley:countries': ({'FR': 2, 'DK': 2, 'DE': 12, 'JP': 4, 'BR': 9, 'FI': 1, 'NL': 6, 'PT': 1, 'MY': 1, 'LT': 1, 'VE': 1, 'CA': 9, 'IT': 4, 'ZA': 4, 'AR': 1, 'AU': 3, 'GB': 17, 'IE': 1, 'ES': 7, 'UA': 1, 'US': 27, 'SG': 1, 'MX': 1, 'SE': 2, 'AT': 1}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley:career_stage': ({u'Researcher (at a non-Academic Institution)': 5, u'Ph.D. Student': 30, u'Student (Bachelor)': 6, u'Student (Postgraduate)': 7, u'Professor': 8, u'Student (Master)': 16, u'Lecturer': 2, u'Assistant Professor': 5, u'Other Professional': 24, u'Doctoral Student': 4, u'Associate Professor': 9, u'Librarian': 48, u'Post Doc': 11, u'Researcher (at an Academic Institution)': 21, u'Senior Lecturer': 2}, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), 'mendeley:readers': (198, u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact')}
        assert_equals(metrics, expected)
       

    @http
    def test_biblio(self):
        # at the moment this item 
        alias = ("doi", "10.1371/journal.pcbi.1000361")
        new_biblio = self.provider.biblio([alias])
        print new_biblio
        expected = {'url': u'http://www.mendeley.com/research/adventures-semantic-publishing-exemplar-semantic-enhancements-research-article', 'abstract': u'Scientific innovation depends on finding, integrating, and re-using the products of previous research. Here we explore how recent developments in Web technology, particularly those related to the publication of data and metadata, might assist that process by providing semantic enhancements to journal articles within the mainstream process of scholarly journal publishing. We exemplify this by describing semantic enhancements we have made to a recent biomedical research article taken from PLoS Neglected Tropical Diseases, providing enrichment to its content and increased access to datasets within it. These semantic enhancements include provision of live DOIs and hyperlinks; semantic markup of textual terms, with links to relevant third-party information resources; interactive figures; a re-orderable reference list; a document summary containing a study summary, a tag cloud, and a citation analysis; and two novel types of semantic enrichment: the first, a Supporting Claims Tooltip to permit "Citations in Context", and the second, Tag Trees that bring together semantically related terms. In addition, we have published downloadable spreadsheets containing data from within tables and figures, have enriched these with provenance information, and have demonstrated various types of data fusion (mashups) with results from other research articles and with Google Maps. We have also published machine-readable RDF metadata both about the article and about the references it cites, for which we developed a Citation Typing Ontology, CiTO (http://purl.org/net/cito/). The enhanced article, which is available at http://dx.doi.org/10.1371/journal.pntd.0000228.x001, presents a compelling existence proof of the possibilities of semantic publication. We hope the showcase of examples and ideas it contains, described in this paper, will excite the imaginations of researchers and publishers, stimulating them to explore the possibilities of semantic publishing for their own research articles, and thereby break down present barriers to the discovery and re-use of information within traditional modes of scholarly communication.', 'issn': u'1553734X'}
        assert_equals(new_biblio, expected) 

    @http
    def test_aliases_doi(self):
        # at the moment this item 
        new_aliases = self.provider.aliases([self.testitem_aliases])
        print new_aliases
        expected = [(u'scopus', u'2-s2.0-82555196668'), (u'pmid', u'22113615'), ('url', u'http://www.mendeley.com/research/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology'), ('mendeley_uuid', u'3021b901-e7a2-393d-acac-3440de7d9523')]
        assert_equals(new_aliases, expected)

    @http
    def test_aliases_no_doi(self):
        # at the moment this item 
        new_aliases = self.provider.aliases([self.testitem_aliases_biblio_no_doi])
        print new_aliases
        expected = [(u'scopus', u'2-s2.0-77956197364'), (u'doi', u'10.5210/fm.v15i7.2874'), ('url', u'http://www.mendeley.com/research/scientometrics-20-toward-new-metrics-scholarly-impact-social-web'), ('mendeley_uuid', u'aa4fa928-b70c-37e9-a16c-34752a41eee2')]
        assert_equals(new_aliases, expected)

    @http
    def test_aliases_biblio(self):
        # at the moment this item 
        alias = (u'biblio', {u'title': u'Altmetrics in the wild: Using social media to explore scholarly impact', u'first_author': u'Priem', u'journal': u'arXiv preprint arXiv:1203.4745', u'authors': u'Priem, Piwowar, Hemminger', u'number': u'', u'volume': u'', u'first_page': u'', u'year': u'2012'})
        new_aliases = self.provider.aliases([alias])
        print new_aliases
        expected = [(u'scopus', u'2-s2.0-84904019573'), (u'doi', u'http://arxiv.org/abs/1203.4745v1'), (u'arxiv', u'1203.4745'), ('url', u'http://www.mendeley.com/research/altmetrics-wild-using-social-media-explore-scholarly-impact'), ('mendeley_uuid', u'dd1ca434-0c00-3d11-8b1f-0226b1d6938c')]
        assert_equals(new_aliases, expected)

