from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, os, re

import logging
logger = logging.getLogger('ti.providers.plosalm')

class Plosalm(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.plos.org/"
    descr = "PLoS article level metrics."
    metrics_url_template = "http://alm.plos.org/articles/%s.json?history=1&api_key=" + os.environ["PLOS_KEY"] + "&events=1"
    provenance_url_template = metrics_url_template

    PLOS_ICON = "http://a0.twimg.com/profile_images/67542107/Globe_normal.jpg"
    PMC_ICON = "http://www.pubmedcentral.gov/corehtml/pmc/pmcgifs/pmclogo.gif"

    static_meta_dict =  {
        "html_views": {
            "display_name": "html views",
            "provider": "PLoS",
            "provider_url": "http://www.plos.org/",
            "description": "the number of views of the PLoS HTML article",
            "icon": PLOS_ICON ,
        },    
        "pdf_views": {
            "display_name": "pdf views",
            "provider": "PLoS",
            "provider_url": "http://www.plos.org/",
            "description": "the number of downloads of the PDF",
            "icon": PLOS_ICON ,
        },    
        "crossref": {
            "display_name": "citations",
            "provider": "CrossRef",
            "provider_url": "http://www.crossref.org",
            "description": "the citation data reported for an article from CrossRef",
            "icon": "http://www.crossref.org/favicon.ico" ,
        },    
        "scopus": {
            "display_name": "citations",
            "provider": "Scopus",
            "provider_url": "http://scopus.com",
            "description": "the citation data reported for an article from Scopus",
            "icon": "http://scopus.com/static/images/favicon.ico" ,
        },    
        "pubmed_central": {
            "display_name": "citations",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the citation data reported for an article from PubMed Central",
            "icon": PMC_ICON,
        },    
        "pmc_figure": {
            "display_name": "figure views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the number of times the figures have been viewed on PubMed Central",
            "icon": PMC_ICON,
        },  
        "pmc_abstract": {
            "display_name": "abstract views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the number of times the abstracts have been viewed on PubMed Central",
            "icon": PMC_ICON,
        },            
        "pmc_full-text": {
            "display_name": "full-text views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the number of times the full-text has been viewed on PubMed Central",
            "icon": PMC_ICON,
        },    
        "pmc_pdf": {
            "display_name": "pdf views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the number of times the pdf has been viewed on PubMed Central",
            "icon": PMC_ICON,
        },    
        "pmc_supp-data": {
            "display_name": "supp-data views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the number of times the supplementary data has been viewed on PubMed Central",
            "icon": PMC_ICON,
        },    
        "pmc_unique-ip": {
            "display_name": "unique-ip views",
            "provider": "PMC",
            "provider_url": "http://www.ncbi.nlm.nih.gov/pmc/",
            "description": "the number of unique IP addresess that have viewed the paper on PubMed Central",
            "icon": PMC_ICON,
        },    
    }
    

    def __init__(self):
        super(Plosalm, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (("doi" == namespace) and ("10.1371/" in nid))
        return(relevant)

    def provenance_url(self, metric_name, aliases, cache_enabled=True):
        id = self.get_best_id(aliases)
        logger.debug("%20s getting provenance for %s %s" % (self.provider_name, id, metric_name))
        if not id:
            return None

        url = self.provenance_url_template % id
        response = self.http_get(url, cache_enabled=cache_enabled)
        if response.status_code != 200:
            if response.status_code == 404:
                return {}
            else:
                raise(self._get_error(response.status_code))
        page = response.text
        data = provider._load_json(page)

        response = "http://www.plosreports.org/services/rest?method=usage.stats&doi=%s" % id
        for source in data["article"]["source"]:
            if self._normalize_source(source["source"]) in metric_name:
                try:
                    response = source["public_url"]
                except KeyError:
                    # this one doesn't have a provenance url, use default
                    pass
        return(response)


    def _normalize_source(self, keyname):
        return(keyname.lower().replace(" ", "_"))

    def _aggregate_monthly_stats(self, metric_name, section):
        total = 0
        for monthly_views in section["events"]:
            total += int(monthly_views[metric_name])
        return (total)

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))
        data = provider._load_json(page)

        metrics_dict = {}
        for section in data["article"]["source"]:
            source = provider._lookup_json(section, ["source"])
            if (source == "Counter"):
                #drilldown_url = provider._lookup_json(section["citations"][0], ["citation", "uri"])
                html_sum = self._aggregate_monthly_stats("html_views", section)
                metrics_dict["html_views"] = html_sum
                pdf_sum = self._aggregate_monthly_stats("pdf_views", section)
                metrics_dict["pdf_views"] = pdf_sum
            elif (source == "PubMed Central Usage Stats"):
                #drilldown_url = provider._lookup_json(section["citations"][0], ["citation", "uri"])
                first_month_stats = section["events"][0]
                for metric_name in first_month_stats:
                    normalized_metric_name = "pmc_" + self._normalize_source(metric_name)
                    if (normalized_metric_name in self.static_meta_dict.keys()):
                        total = self._aggregate_monthly_stats(metric_name, section)
                        metrics_dict[normalized_metric_name] = total
            elif (self._normalize_source(source) in self.static_meta_dict.keys()):
                total = provider._lookup_json(section, ["count"])
                if total:
                    #drilldown_url = provider._lookup_json(section, ["public_url"])
                    #if not drilldown_url:
                    #    drilldown_url = ""
                    metrics_dict[source] = total

        rekeyed_dict = dict(("plosalm:"+self._normalize_source(k),v) for (k,v) in metrics_dict.iteritems())

        return rekeyed_dict


