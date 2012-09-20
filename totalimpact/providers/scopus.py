from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, re, os, random, string

import logging
logger = logging.getLogger('ti.providers.scopus')

class Scopus(Provider):  

    example_id = ("doi", "10.1371/journal.pone.0000308")

    url = "http://www.info.sciverse.com/scopus/about"
    descr = "The world's largest abstract and citation database of peer-reviewed literature."
    # template urls below because they need a freshly-minted random string
    metrics_url_template = None
    provenance_url_template = None

    static_meta_dict =  { 
        "citations": {
            "display_name": "citations",
            "provider": "Scopus",
            "provider_url": "http://www.info.sciverse.com/scopus/about",
            "description": "Number of times the item has been cited",
            "icon": "http://www.info.sciverse.com/sites/all/themes/sciverse/favicon.ico" ,
        }
    }
    

    def __init__(self):
        super(Scopus, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)


    def _extract_metrics(self, fullpage, status_code=200, id=None):
        try:
            # extract json from inside the first and last parens
            # from http://codereview.stackexchange.com/questions/2561/converting-jsonp-to-json-is-this-regex-correct
            page = fullpage[ fullpage.index("(")+1 : fullpage.rindex(")") ]
        except ValueError:
            raise ProviderContentMalformedError()

        data = provider._load_json(page)
        try:
            citations = int(data["OK"]["results"][0]["citedbycount"])
        except (KeyError, ValueError):
            # not in Scopus database
            return {}

        metrics_dict = {}
        if citations:
            metrics_dict["scopus:citations"] = citations
        return metrics_dict

    def _extract_provenance_url(self, fullpage, status_code=200, id=None):
        try:
            # extract json from inside the first and last parens
            # from http://codereview.stackexchange.com/questions/2561/converting-jsonp-to-json-is-this-regex-correct
            page = fullpage[ fullpage.index("(")+1 : fullpage.rindex(")") ]
        except ValueError:
            return ""
        data = provider._load_json(page)
        try:
            provenance_url = data["OK"]["results"][0]["inwardurl"]
        except KeyError:
            provenance_url = ""
        return provenance_url        


    def _get_metrics_and_drilldown_from_metrics_page(self, page):
        metrics_dict = self._extract_metrics(page)
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self._extract_provenance_url(page)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown  

    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None, # ignore this because multiple url steps
            cache_enabled=True):


        id = self.get_best_id(aliases)
        # Only lookup metrics for items with appropriate ids
        if not id:
            #self.logger.debug("%s not checking metrics, no relevant alias" % (self.provider_name))
            return {}

        # use the doi without punctuation, so that can cache
        random_string = "".join(ch for ch in id if ch in string.letters)
        self.metrics_url_template = 'http://searchapi.scopus.com/documentSearch.url?&search="%s"&callback=sciverse.Backend._requests.search1.callback&preventCache='+random_string+"&apiKey="+os.environ["SCOPUS_KEY"]
        self.provenance_url_template = self.metrics_url_template

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        url = self._get_templated_url(provider_url_template, id, "metrics")

        response = self.http_get(url)
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            else:
                raise(self._get_error(response.status_code))
        page = response.text
        if not page:
            raise ProviderContentMalformedError()

        metrics_and_drilldown = self._get_metrics_and_drilldown_from_metrics_page(page)

        return metrics_and_drilldown
