from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, urllib, os

import logging
logger = logging.getLogger('ti.providers.pubmed')

class Pubmed(Provider):  

    example_id = ("pmid", "22855908")

    url = "http://pubmed.gov"
    descr = "PubMed comprises more than 21 million citations for biomedical literature"
    provenance_url_template = "http://www.ncbi.nlm.nih.gov/pubmed/%s"

    metrics_url_template = "http://www.pubmedcentral.nih.gov/utils/entrez2pmcciting.cgi?view=xml&id=%s"

    aliases_from_doi_url_template = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?term=%s&email=team@total-impact.org&tool=total-impact" 
    aliases_from_pmid_url_template = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=%s&retmode=xml&email=team@total-impact.org&tool=total-impact" 

    static_meta_dict = {
        "pmc_citations": {
            "display_name": "citations",
            "provider": "PubMed Central",
            "provider_url": "http://pubmed.gov",
            "description": "The number of citations by papers in PubMed Central",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        } 
    }


    def __init__(self):
        super(Pubmed, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (namespace=="pmid")
        return(relevant)

    def _get_aliases_page(self, id, url_template, cache_enabled):
        logger.debug("%20s getting aliases for %s" % (self.provider_name, id))

        url = url_template %id
        response = self.http_get(url, cache_enabled=cache_enabled)
        if response.status_code != 200:
            logger.warning("%20s WARNING, status_code=%i getting %s" 
                % (self.provider_name, response.status_code, url))            
            if response.status_code == 404:
                return []
            else:
                self._get_error(response.status_code, response)
        return response.text

    def _extract_aliases_from_doi(self, page):
        dict_of_keylists = {"pmid": ["eSearchResult", "IdList", "Id"]}

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list


    def _extract_aliases_from_pmid(self, page):
        dict_of_keylists = {"doi": ["PubmedData", "ArticleIdList"]}

        (doc, lookup_function) = provider._get_doc_from_xml(page)
        try:
            articleidlist = doc.getElementsByTagName("ArticleIdList")[0]
            for articleid in articleidlist.getElementsByTagName("ArticleId"):
                if (articleid.getAttribute("IdType") == u"doi"):
                    doi = articleid.firstChild.data
        except (IndexError, TypeError):
            doi = None

        if doi:
            aliases_list = [("doi", doi)]
        else:
            aliases_list = []
        return aliases_list

    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    # default method; providers can override
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        new_aliases = aliases[:]
        for alias in aliases:
            (namespace, nid) = alias
            if (namespace == "doi"):
                page = self._get_aliases_page(nid, self.aliases_from_doi_url_template, cache_enabled)
                new_aliases += self._extract_aliases_from_doi(page)
            if (namespace == "pmid"):
                page = self._get_aliases_page(nid, self.aliases_from_pmid_url_template, cache_enabled)
                new_aliases += self._extract_aliases_from_pmid(page)

        new_aliases_unique = list(set(new_aliases))
        return new_aliases_unique


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if (not "PubMedToPMCcitingformSET" in page):
            raise ProviderContentMalformedError()

        dict_of_keylists = {"pubmed:pmc_citations": ["PubMedToPMCcitingformSET", "REFORM"]}
        (doc, lookup_function) = provider._get_doc_from_xml(page)

        pmcid_doms = doc.getElementsByTagName("PMCID")
        pmcids = [pmcid_dom.firstChild.data for pmcid_dom in pmcid_doms]
        metrics_dict = {}
        metrics_dict["pubmed:pmc_citations"] = len(pmcids)

        return metrics_dict


