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


    def _get_json(self, fullpage, id):
        try:
            # extract json from inside the first and last parens
            # from http://codereview.stackexchange.com/questions/2561/converting-jsonp-to-json-is-this-regex-correct
            page = fullpage[ fullpage.index("(")+1 : fullpage.rindex(")") ]
        except ValueError:
            raise ProviderContentMalformedError()

        data = provider._load_json(page)
        return(data)

    def _get_relevant_record(self, fullpage, id):
        data = self._get_json(fullpage, id)
        response = None
        try:
            citation_rows = data["OK"]["results"]
            for citation_row in citation_rows:
                if citation_row["doi"]==id:
                    response = citation_row
        except (KeyError, ValueError):
            # not in Scopus database
            return None
        return response

    def _extract_metrics(self, fullpage, status_code=200, id=None):
        record = self._get_relevant_record(fullpage, id)
        try:
            citations = int(record["citedbycount"])    
        except (KeyError, TypeError):
            return {}

        if citations:
            metrics_dict = {"scopus:citations": citations}
        else:
            metrics_dict = {}                    
        return metrics_dict

    def _extract_provenance_url(self, fullpage, status_code=200, id=None):
        record = self._get_relevant_record(fullpage, id)
        try:
            provenance_url = record["inwardurl"] 
        except (KeyError, TypeError):
            provenance_url = ""
        return provenance_url

    def _get_page(self, url):
        response = self.http_get(url, timeout=30)
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            else:
                raise(self._get_error(response.status_code))
        page = response.text
        if not page:
            raise ProviderContentMalformedError()
        return page

    def _get_page_with_doi(self, provider_url_template, id):
        # pick a new random string so don't time out.  Unfort, url now can't cache.
        random_string = "".join(random.sample(string.letters, 10))
        self.metrics_url_template = 'http://searchapi.scopus.com/documentSearch.url?&search=%s&callback=sciverse.Backend._requests.search1.callback&preventCache='+random_string+"&apiKey="+os.environ["SCOPUS_KEY"]
        self.provenance_url_template = self.metrics_url_template

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        logger.debug("id = {id}".format(id=id))
        logger.debug("provider_url_template = {provider_url_template}".format(
            provider_url_template=provider_url_template))

        url = self._get_templated_url(provider_url_template, id, "metrics")
        page = self._get_page(url)
        if "Result set was empty" in page:
            return None
        relevant_record = self._get_relevant_record(page, id)
        if not relevant_record:
            data = self._get_json(page, id)
            try:
                number_results = data["OK"]["totalResults"]
            except (KeyError, ValueError):
                return None            
            url = "{previous_url}&offset={last_record}".format(
                previous_url=url, last_record=(int(number_results)-1))
            page = self._get_page(url)
            relevant_record = self._get_relevant_record(page, id)
            if not relevant_record:
                logging.warning("not empty result set, yet couldn't find a page with doi {id}".format(id=id))
                return None
        return page

    def _get_metrics_and_drilldown_from_metrics_page(self, provider_url_template, id):
        page = self._get_page_with_doi(provider_url_template, id)
        if not page:
            logging.info("no scopus page with doi {id}".format(id=id))
            return {}
        metrics_dict = self._extract_metrics(page, id=id)
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self._extract_provenance_url(page, id=id)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown  

    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        id = self.get_best_id(aliases)
        # Only lookup metrics for items with appropriate ids
        if not id:
            #self.logger.debug("%s not checking metrics, no relevant alias" % (self.provider_name))
            return {}

        metrics_and_drilldown = self._get_metrics_and_drilldown_from_metrics_page(provider_url_template, id=id)

        return metrics_and_drilldown
