from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, re, os, random, string, urllib

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


    def _get_json(self, fullpage):
        try:
            # extract json from inside the first and last parens
            # from http://codereview.stackexchange.com/questions/2561/converting-jsonp-to-json-is-this-regex-correct
            page = fullpage[ fullpage.index("(")+1 : fullpage.rindex(")") ]
        except (AttributeError, ValueError):
            raise ProviderContentMalformedError()

        data = provider._load_json(page)
        return(data)



    def _extract_metrics(self, record, status_code=200, id=None):
        try:
            citations = int(record["citedbycount"])    
        except (KeyError, TypeError, ValueError):
            return {}

        if citations:
            metrics_dict = {"scopus:citations": citations}
        else:
            metrics_dict = {}                    
        return metrics_dict

    def _extract_provenance_url(self, record, status_code=200, id=None):
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
                raise(self._get_error(response.status_code, response))
        page = response.text
        if not page:
            raise ProviderContentMalformedError()
        return page

    def _extract_relevant_record_with_doi(self, fullpage, id):
        data = self._get_json(fullpage)
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

    def _get_scopus_page(self, url):
        page = self._get_page(url)
        if not page:
            logging.info("empty page with id {id}".format(id=id))
            return None
        if "Result set was empty" in page:
            #logging.warning("empty result set with doi {id}".format(id=id))
            return None
        return page


    def _get_relevant_record_with_doi(self, id):
        # pick a new random string so don't time out.  Unfort, url now can't cache.
        random_string = "".join(random.sample(string.letters, 10))
        url_template = 'http://searchapi.scopus.com/documentSearch.url?&search=%s&callback=sciverse.Backend._requests.search1.callback&preventCache='+random_string+"&apiKey="+os.environ["SCOPUS_KEY"]
        url = self._get_templated_url(url_template, id)

        page = self._get_scopus_page(url)
        if not page:
            return None  # empty result set

        relevant_record = self._extract_relevant_record_with_doi(page, id)
        if not relevant_record:
            data = self._get_json(page)
            try:
                number_results = data["OK"]["totalResults"]
            except (KeyError, ValueError):
                return None            
            url = "{previous_url}&offset={last_record}".format(
                previous_url=url, last_record=(int(number_results)-1))
            page = self._get_page(url)
            relevant_record = self._extract_relevant_record_with_doi(page, id)
            if not relevant_record:
                logging.warning("not empty result set, yet couldn't find a page with doi {id}".format(id=id))
                return None
        return relevant_record

    def _extract_relevant_record_with_biblio(self, fullpage, id):
        scopus_data = self._get_json(fullpage)
        relevant_record = None
        try:
            citation_rows = scopus_data["OK"]["results"]
            if len(citation_rows)==1:
                relevant_record = citation_rows[0]
            else:
                #logging.warning("ambiguous result set with biblio, not selecting any {id}".format(id=id))
                return None
        except (KeyError, ValueError):
            # not in Scopus database
            return None
        return relevant_record

    def _get_relevant_record_with_biblio(self, biblio_dict):
        random_string = "".join(random.sample(string.letters, 10))
        url_template = "http://searchapi.scopus.com/documentSearch.url?&search=First%20Author:{first_author};Journal:%22{journal}%22;Title:{title}&callback=sciverse.Backend._requests.search1.callback&preventCache="+random_string+"&apiKey="+os.environ["SCOPUS_KEY"]
        try:        
            url = url_template.format(
                    first_author=urllib.quote(biblio_dict["first_author"]), 
                    title=urllib.quote(biblio_dict["title"]), 
                    journal=urllib.quote(biblio_dict["journal"]))
        except KeyError:
            return None
        page = self._get_scopus_page(url)
        if not page:
            return None  # empty result set

        relevant_record = self._extract_relevant_record_with_biblio(page, biblio_dict)
        return relevant_record


    def _get_metrics_and_drilldown_from_metrics_page(self, provider_url_template, namespace, id):
        relevant_record = None
        if namespace=="doi":
            relevant_record = self._get_relevant_record_with_doi(id)
        elif namespace=="biblio":
            relevant_record = self._get_relevant_record_with_biblio(id)

        if not relevant_record:
            logging.info("no scopus page with id {id}".format(id=id))
            return {}

        metrics_dict = self._extract_metrics(relevant_record)
        
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self._extract_provenance_url(relevant_record)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown  


    def get_best_alias(self, aliases_dict):
        for namespace in ["doi", "biblio"]:
            if namespace in aliases_dict:
                return (namespace, aliases_dict[namespace][0])
        return (None, None)

    # custom, because uses doi if available, else biblio
    def metrics(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        aliases_dict = provider.alias_dict_from_tuples(aliases)
        (namespace, nid) = self.get_best_alias(aliases_dict)
        if not nid:
            #self.logger.debug("%s not checking metrics, no relevant alias" % (self.provider_name))
            return {}

        metrics_and_drilldown = self._get_metrics_and_drilldown_from_metrics_page(provider_url_template, 
                namespace=namespace, 
                id=nid)

        return metrics_and_drilldown
