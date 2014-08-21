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

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/mendeley")
SAMPLE_EXTRACT_UUID_PAGE = os.path.join(datadir, "uuidlookup")
SAMPLE_EXTRACT_UUID_PAGE_NO_DOI = os.path.join(datadir, "uuidlookup_no_doi")
SAMPLE_EXTRACT_METRICS_PAGE = os.path.join(datadir, "metrics")
SAMPLE_EXTRACT_PROVENANCE_URL_PAGE = SAMPLE_EXTRACT_METRICS_PAGE
SAMPLE_EXTRACT_BIBLIO_PAGE = os.path.join(datadir, "biblio")
SAMPLE_EXTRACT_BIBLIO_PAGE_OAI = os.path.join(datadir, "biblio_oai")

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
  
    def test_extract_biblio_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE, "r")
        biblio_dict = self.provider._extract_biblio(f.read())
        print biblio_dict
        expected = {'abstract': 'Tuberous sclerosis complex and fragile X syndrome are genetic diseases characterized by intellectual disability and autism. Because both syndromes are caused by mutations in genes that regulate protein synthesis in neurons, it has been hypothesized that excessive protein synthesis is one core pathophysiological mechanism of intellectual disability and autism. Using electrophysiological and biochemical assays of neuronal protein synthesis in the hippocampus of Tsc2(+/-) and Fmr1(-/y) mice, here we show that synaptic dysfunction caused by these mutations actually falls at opposite ends of a physiological spectrum. Synaptic, biochemical and cognitive defects in these mutants are corrected by treatments that modulate metabotropic glutamate receptor 5 in opposite directions, and deficits in the mutants disappear when the mice are bred to carry both mutations. Thus, normal synaptic plasticity and cognition occur within an optimal range of metabotropic glutamate-receptor-mediated protein synthesis, and deviations in either direction can lead to shared behavioural impairments.', 'issn': '00280836', 'is_oa_journal': 'False'}
        assert_equals(biblio_dict, expected)

    def test_extract_biblio_oai_success(self):
        f = open(SAMPLE_EXTRACT_BIBLIO_PAGE_OAI, "r")
        biblio_dict = self.provider._extract_biblio(f.read())
        print biblio_dict
        expected = {'oai_id': 'oai:arXiv.org:1012.4872', 'abstract': "Google's PageRank has created a new synergy to information retrieval for a better ranking of Web pages. It ranks documents depending on the topology of the graphs and the weights of the nodes. PageRank has significantly advanced the field of information retrieval and keeps Google ahead of competitors in the search engine market. It has been deployed in bibliometrics to evaluate research impact, yet few of these studies focus on the important impact of the damping factor (d) for ranking purposes. This paper studies how varied damping factors in the PageRank algorithm can provide additional insight into the ranking of authors in an author co-citation network. Furthermore, we propose weighted PageRank algorithms. We select 108 most highly cited authors in the information retrieval (IR) area from the 1970s to 2008 to form the author co-citation network. We calculate the ranks of these 108 authors based on PageRank with damping factor ranging from 0.05 to 0.95. In order to test the relationship between these different measures, we compare PageRank and weighted PageRank results with the citation ranking, h-index, and centrality measures. We found that in our author co-citation network, citation rank is highly correlated with PageRank's with different damping factors and also with different PageRank algorithms; citation rank and PageRank are not significantly correlated with centrality measures; and h-index is not significantly correlated with centrality measures.", 'issn': '15322882', 'is_oa_journal': 'None'}
        assert_equals(biblio_dict, expected)

    def test_extract_metrics_success(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        metrics_dict = self.provider._extract_metrics(f.read())
        assert_equals(metrics_dict["mendeley:readers"], 102)

    def test_extract_provenance_url(self):
        f = open(SAMPLE_EXTRACT_PROVENANCE_URL_PAGE, "r")
        provenance_url = self.provider._extract_provenance_url(f.read())
        assert_equals(provenance_url, "http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/")

    def test_get_ids_from_title(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE, "r")
        response = self.provider._get_uuid_from_title(self.testitem_metrics_dict, f.read())
        expected = {'uuid': '1f471f70-1e4f-11e1-b17d-0024e8453de6'}
        assert_equals(response, expected)

    def test_get_ids_from_title_no_doi(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE_NO_DOI, "r")
        response = self.provider._get_uuid_from_title(self.testitem_metrics_dict, f.read())
        print response
        expected = {'url': 'http://www.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/', 'uuid': '1f471f70-1e4f-11e1-b17d-0024e8453de6'}
        assert_equals(response, expected)

    def test_get_ids_from_title_no_doi_wrong_year(self):
        f = open(SAMPLE_EXTRACT_UUID_PAGE_NO_DOI, "r")
        response = self.provider._get_uuid_from_title(self.testitem_metrics_dict_wrong_year, f.read())
        expected = None
        assert_equals(response, expected)

    def test_get_metrics_and_drilldown_from_metrics_page(self):
        f = open(SAMPLE_EXTRACT_METRICS_PAGE, "r")
        response = self.provider._get_metrics_and_drilldown_from_metrics_page(f.read())
        expected = {'mendeley:discipline': ([{'id': 3, 'value': 80, 'name': 'Biological Sciences'}, {'id': 19, 'value': 14, 'name': 'Medicine'}, {'id': 22, 'value': 2, 'name': 'Psychology'}], 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:country': ([{'name': 'United States', 'value': 42}, {'name': 'Japan', 'value': 12}, {'name': 'United Kingdom', 'value': 9}], 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:career_stage': ([{'name': 'Ph.D. Student', 'value': 31}, {'name': 'Post Doc', 'value': 21}, {'name': 'Professor', 'value': 7}], 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/'), 'mendeley:readers': (102, 'http://api.mendeley.com/catalog/mutations-causing-syndromic-autism-define-axis-synaptic-pathophysiology/')}
        assert_equals(response, expected)

    def test_remove_punctuation(self):
        response = self.provider.remove_punctuation(u"sdflkdsjf4r42432098@#$#@$sdlkfj..sdfsdf")
        assert_equals(response, u'sdflkdsjf4r42432098sdlkfjsdfsdf')

    @http
    def test_metrics_pmid(self):
        # at the moment this item 
        metrics_dict = self.provider.metrics([("pmid", "12578738")])
        expected = {'mendeley:discipline': ([{u'id': 6, u'value': 33, u'name': u'Computer and Information Science'}, {u'id': 3, u'value': 33, u'name': u'Biological Sciences'}, {u'id': 19, u'value': 12, u'name': u'Medicine'}], u'http://api.mendeley.com/catalog/value-data/'), 
                'mendeley:country': ([{u'name': u'United States', u'value': 22}, {u'name': u'United Kingdom', u'value': 16}, {u'name': u'Netherlands', u'value': 12}], u'http://api.mendeley.com/catalog/value-data/'), 
                'mendeley:career_stage': ([{u'name': u'Ph.D. Student', u'value': 19}, {u'name': u'Other Professional', u'value': 15}, {u'name': u'Researcher (at an Academic Institution)', u'value': 14}], u'http://api.mendeley.com/catalog/value-data/'), 
                'mendeley:readers': (129, u'http://api.mendeley.com/catalog/value-data/')}
        print metrics_dict
        assert_equals(set(metrics_dict.keys()), set(expected.keys())) 
        # can't tell more about dicsciplines etc because they are percentages and may go up or down

    @http
    def test_metrics_arxiv(self):
        # at the moment this item 
        metrics = self.provider.metrics([("arxiv", "1203.4745")])
        print metrics
        expected = {'mendeley:discipline': ([{u'id': 6, u'value': 35, u'name': u'Computer and Information Science'}, {u'id': 23, u'value': 24, u'name': u'Social Sciences'}, {u'id': 19, u'value': 8, u'name': u'Medicine'}], u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), 'mendeley:country': ([{u'name': u'United States', u'value': 14}, {u'name': u'United Kingdom', u'value': 9}, {u'name': u'Germany', u'value': 6}], u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), 'mendeley:career_stage': ([{u'name': u'Librarian', u'value': 25}, {u'name': u'Ph.D. Student', u'value': 15}, {u'name': u'Other Professional', u'value': 12}], u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), 'mendeley:readers': (190, u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/')}
        assert_equals(metrics, expected)

    @http
    def test_aliases_no_doi(self):
        # at the moment this item 
        new_aliases = self.provider.aliases([self.testitem_aliases_biblio_no_doi])
        print new_aliases
        expected = [('doi', u'10.5210/fm.v15i7.2874'), ('url', u'http://www.mendeley.com/catalog/scientometrics-20-toward-new-metrics-scholarly-impact-social-web/'), ('uuid', u'16e2f482-54f1-3934-a587-9ca3a70c4a7c')]
        assert_equals(new_aliases, expected)

    @http
    def test_aliases_biblio(self):
        # at the moment this item 
        alias = (u'biblio', {u'title': u'Altmetrics in the wild: Using social media to explore scholarly impact', u'first_author': u'Priem', u'journal': u'arXiv preprint arXiv:1203.4745', u'authors': u'Priem, Piwowar, Hemminger', u'number': u'', u'volume': u'', u'first_page': u'', u'year': u'2012'})
        new_aliases = self.provider.aliases([alias])
        print new_aliases
        expected = [('doi', u'http://arxiv.org/abs/1203.4745v1'), ('url', u'http://www.mendeley.com/catalog/altmetrics-wild-using-social-media-explore-scholarly-impact/'), ('uuid', u'dd1ca434-0c00-3d11-8b1f-0226b1d6938c')]
        assert_equals(new_aliases, expected)

    @http
    def test_biblio_oai_id(self):
        # at the moment this item 
        alias = ("doi", "10.1086/508600")
        new_biblio = self.provider.biblio([alias])
        print new_biblio
        expected = {'oai_id': u'oai:arXiv.org:astro-ph/0603060', 'abstract': u'We determine the shape, multiplicity, size, and radial structure of superclusters in the LambdaCDM concordance cosmology from z = 0 to z = 2. Superclusters are defined as clusters of clusters in our large-scale cosmological simulation. We find that superclusters are triaxial in shape; many have flattened since early times to become nearly two-dimensional structures at present, with a small fraction of filamentary systems. The size and multiplicity functions are presented at different redshifts. Supercluster sizes extend to scales of ~ 100 - 200 Mpc/h. The supercluster multiplicity (richness) increases linearly with supercluster size. The density profile in superclusters is approximately isothermal (~ R^{-2}) and steepens on larger scales. These results can be used as a new test of the current cosmology when compared with upcoming observations of large-scale surveys.', 'issn': u'0004637X', 'is_oa_journal': 'None'}
        assert_equals(new_biblio, expected)        

    @http
    def test_biblio_issn(self):
        # at the moment this item 
        alias = ("doi", "10.1371/journal.pcbi.1000361")
        new_biblio = self.provider.biblio([alias])
        print new_biblio
        expected = {'oai_id': u'oai:pubmedcentral.nih.gov:2663789', 'abstract': u'Scientific innovation depends on finding, integrating, and re-using the products of previous research. Here we explore how recent developments in Web technology, particularly those related to the publication of data and metadata, might assist that process by providing semantic enhancements to journal articles within the mainstream process of scholarly journal publishing. We exemplify this by describing semantic enhancements we have made to a recent biomedical research article taken from PLoS Neglected Tropical Diseases, providing enrichment to its content and increased access to datasets within it. These semantic enhancements include provision of live DOIs and hyperlinks; semantic markup of textual terms, with links to relevant third-party information resources; interactive figures; a re-orderable reference list; a document summary containing a study summary, a tag cloud, and a citation analysis; and two novel types of semantic enrichment: the first, a Supporting Claims Tooltip to permit "Citations in Context", and the second, Tag Trees that bring together semantically related terms. In addition, we have published downloadable spreadsheets containing data from within tables and figures, have enriched these with provenance information, and have demonstrated various types of data fusion (mashups) with results from other research articles and with Google Maps. We have also published machine-readable RDF metadata both about the article and about the references it cites, for which we developed a Citation Typing Ontology, CiTO (http://purl.org/net/cito/). The enhanced article, which is available at http://dx.doi.org/10.1371/journal.pntd.0000228.x001, presents a compelling existence proof of the possibilities of semantic publication. We hope the showcase of examples and ideas it contains, described in this paper, will excite the imaginations of researchers and publishers, stimulating them to explore the possibilities of semantic publishing for their own research articles, and thereby break down present barriers to the discovery and re-use of information within traditional modes of scholarly communication.', 'issn': u'1553734X', 'free_fulltext_url': 'http://dx.doi.org/10.1371/journal.pcbi.1000361', 'is_oa_journal': 'True'}
        assert_equals(new_biblio, expected) 

    # override common tests
    @raises(ProviderClientError, ProviderServerError)
    def test_provider_metrics_400(self):
        Provider.http_get = common.get_400
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderServerError)
    def test_provider_metrics_500(self):
        Provider.http_get = common.get_500
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderClientError, ProviderServerError)
    def test_provider_aliases_400(self):
        Provider.http_get = common.get_400
        metrics = self.provider.aliases([self.testitem_aliases_biblio_no_doi])

    @raises(ProviderServerError)
    def test_provider_aliases_500(self):
        Provider.http_get = common.get_500
        metrics = self.provider.aliases([self.testitem_aliases_biblio_no_doi])

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_empty(self):
        Provider.http_get = common.get_empty
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_txt(self):
        Provider.http_get = common.get_nonsense_txt
        metrics = self.provider.metrics(self.testitem_metrics)

    @raises(ProviderContentMalformedError)
    def test_provider_metrics_nonsense_xml(self):
        Provider.http_get = common.get_nonsense_xml
        metrics = self.provider.metrics(self.testitem_metrics)

    def test_provider_biblio_400(self):
        pass
    def test_provider_biblio_500(self):
        pass

