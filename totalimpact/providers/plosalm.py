from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, os, re, urllib

import logging
logger = logging.getLogger('ti.providers.plosalm')

class Plosalm(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.plos.org/"
    descr = "PLOS article level metrics."
    metrics_url_template = "http://alm.plos.org/api/v3/articles?ids=%s&source=citations,counter&api_key=" + os.environ["PLOS_KEY_V3"]
    provenance_url_template = "http://dx.doi.org/%s"

    PLOS_ICON = "http://www.plos.org/wp-content/themes/plos_new/favicon.ico"

    static_meta_dict =  {
        "html_views": {
            "display_name": "html views",
            "provider": "PLOS",
            "provider_url": "http://www.plos.org/",
            "description": "the number of views of the HTML article on PLOS",
            "icon": PLOS_ICON,
        },    
        "pdf_views": {
            "display_name": "pdf views",
            "provider": "PLOS",
            "provider_url": "http://www.plos.org/",
            "description": "the number of downloads of the PDF from PLOS",
            "icon": PLOS_ICON,
        }  
    }
    

    def __init__(self):
        super(Plosalm, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (("doi" == namespace) and ("10.1371/" in nid))
        return(relevant)

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "sources" in page:
            raise ProviderContentMalformedError

        json_response = provider._load_json(page)
        this_article = json_response[0]["sources"][0]["metrics"]

        dict_of_keylists = {
            'plosalm:html_views' : ['html'],
            'plosalm:pdf_views' : ['pdf']
        }

        metrics_dict = provider._extract_from_data_dict(this_article, dict_of_keylists)

        return metrics_dict


