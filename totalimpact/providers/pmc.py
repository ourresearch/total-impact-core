from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import hashlib
import simplejson

import logging
logger = logging.getLogger('ti.providers.pmc')

class Pmc(Provider):  

    example_id = ("pmid", "23066504")
    provenance_url_template = None
    url = "http://www.ncbi.nlm.nih.gov/pmc"
    descr = "a free archive of biomedical and life sciences journal literature at the NIH/NLM"
    static_meta_dict = {
        "pdf_downloads": {
            "display_name": "PDF downloads",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc",
            "description": "Number of times the PDF has been downloaded from PMC",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        },
        "abstract_views": {
            "display_name": "abstract views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc",
            "description": "Number of times the abstract has been viewed on PMC",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        },        
        "fulltext_views": {
            "display_name": "fulltext views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc",
            "description": "Number of times the full text has been viewed on PMC",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        },        
        "unique_ip_views": {
            "display_name": "unique IP views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc",
            "description": "Number of unique IP addresses that have viewed this on PMC",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        },         
        "figure_views": {
            "display_name": "figure views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc",
            "description": "Number of times the figures have been viewed on PMC",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        },        
        "suppdata_views": {
            "display_name": "suppdata views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc",
            "description": "Number of times the supplementary data has been viewed on PMC",
            "icon": "http://www.ncbi.nlm.nih.gov/favicon.ico"
        }               
    }

    def __init__(self):
        super(Pmc, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("pmid" == namespace)

    def _extract_metrics(self, page, status_code=200, id=None): 
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if "<pmc-web-stat>" not in page:
            raise ProviderContentMalformedError

        (doc, lookup_function) = provider._get_doc_from_xml(page)  
        if not doc:
            return {}
        metrics_dict = {}            
        try:
            number_downloads = None
            articles = doc.getElementsByTagName("article")
            for article in articles:
                meta_data = article.getElementsByTagName("meta-data")[0]
                pmid = meta_data.getAttribute("pubmed-id")
                if id == pmid:
                    metrics = article.getElementsByTagName("usage")[0]
                    pdf_downloads = int(metrics.getAttribute("pdf"))
                    if pdf_downloads:
                        metrics_dict.update({'pmc:pdf_downloads': pdf_downloads})

                    abstract_views = int(metrics.getAttribute("abstract"))
                    if abstract_views:
                        metrics_dict.update({'pmc:abstract_views': abstract_views})

                    fulltext_views = int(metrics.getAttribute("full-text"))
                    if fulltext_views:
                        metrics_dict.update({'pmc:fulltext_views': fulltext_views})

                    unique_ip = int(metrics.getAttribute("unique-ip"))
                    if unique_ip:
                        metrics_dict.update({'pmc:unique_ip': unique_ip})

                    figure_views = int(metrics.getAttribute("figure"))
                    if figure_views:
                        metrics_dict.update({'pmc:figure_views': figure_views})

                    suppdata_views = int(metrics.getAttribute("supp-data"))
                    if suppdata_views:
                        metrics_dict.update({'pmc:suppdata_views': suppdata_views})

        except (KeyError, IndexError, TypeError):
            return {}

        return metrics_dict

    def _get_metrics_and_drilldown(self, page=""):
        metrics_dict = self._extract_metrics(page)
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = ""
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown

    def metrics(self, 
            aliases,
            provider_url_template=None, # ignore this because multiple url steps
            cache_enabled=True):

        # Only lookup metrics for items with appropriate ids
        from totalimpact.models import ItemFactory
        aliases_dict = ItemFactory.alias_dict_from_tuples(aliases)

        metrics_and_drilldown = self._get_metrics_and_drilldown()

        return metrics_and_drilldown


