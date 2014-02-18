from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, re, os, urllib

import logging
logger = logging.getLogger('ti.providers.plossearch')

class Plossearch(Provider):  

    example_id = ("doi", "10.5061/dryad.c2b53")

    url = "http://www.plos.org/"
    descr = "PLoS article level metrics."
    metrics_url_template = 'http://api.plos.org/search?q="%s"&api_key=' + os.environ["PLOS_KEY_V3"]
    provenance_url_template = 'http://www.plosone.org/search/advanced?queryTerm=&unformattedQuery=everything:"%s"'

    static_meta_dict =  {
        "mentions": {
            "display_name": "mentions",
            "provider": "PLOS",
            "provider_url": "http://www.plos.org/",
            "description": "the number of times the research product was mentioned in the full-text of PLOS papers",
            "icon": "http://www.plos.org/wp-content/themes/plos_new/favicon.ico" ,
        }
    } 

    def __init__(self):
        super(Plossearch, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if namespace in ["url", "doi"]:
            for host in ["dryad", "figshare", "github", "youtube", "vimeo", "arxiv"]:
                if host in nid:
                    return True
        return False

    def get_best_id(self, aliases):
        return self.get_relevant_alias_with_most_metrics("plossearch:mentions", aliases)

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "<response>" in page:
            raise ProviderContentMalformedError

        count = provider._count_in_xml(page, 'doc')
        if count:
            metrics_dict = {'plossearch:mentions': count}
        else:
            metrics_dict = {}

        return metrics_dict

    # need to override to url encode for metrics
    def _get_templated_url(self, template, id, method=None):
        id = re.sub('^http(s?)://', '', id)
        try:
            id = urllib.quote(id, safe="")
        except KeyError:  # thrown if bad characters
            pass
        url = template % id
        return(url)

