from totalimpact.providers import provider
from totalimpact.providers import crossref
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson

import logging
logger = logging.getLogger('ti.providers.figshare')

class Figshare(Provider):  

    example_id = ("doi", "10.6084/m9.figshare.92393")

    url = "http://figshare.com"
    descr = "Make all of your research outputs sharable, citable and visible in the browser for free."
    biblio_url_template = "http://api.figshare.com/v1/articles/%s"
    aliases_url_template = "http://api.figshare.com/v1/articles/%s"
    metrics_url_template = "http://api.figshare.com/v1/articles/%s"
    provenance_url_template = "http://dx.doi.org/%s"

    static_meta_dict = {
        "shares": {
            "display_name": "shares",
            "provider": "figshare",
            "provider_url": "http://figshare.com",
            "description": "The number of times this has been shared",
            "icon": "http://figshare.com/static/img/favicon.png",
        },
        "downloads": {
            "display_name": "downloads",
            "provider": "figshare",
            "provider_url": "http://figshare.com",
            "description": "The number of times this has been downloaded",
            "icon": "http://figshare.com/static/img/favicon.png",
            },
        "views": {
            "display_name": "views",
            "provider": "figshare",
            "provider_url": "http://figshare.com",
            "description": "The number of times this item has been viewed",
            "icon": "http://figshare.com/static/img/favicon.png",
            }
    }     

    def __init__(self):
        super(Figshare, self).__init__()
        self.crossref = crossref.Crossref()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        is_figshare_doi = (namespace == "doi") and (".figshare." in nid.lower())
        return is_figshare_doi

    @property
    def provides_aliases(self):
         return True

    @property
    def provides_biblio(self):
         return True

    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):  
        logger.info("calling crossref to handle aliases")
        return self.crossref.aliases(aliases, provider_url_template, cache_enabled)          

    def biblio(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):  
        logger.info("calling crossref to handle aliases")
        return self.crossref.biblio(aliases, provider_url_template, cache_enabled) 

    def _extract_figshare_record(self, page, id):
        data = provider._load_json(page)
        if not data:
            return {}
        item = data["items"][0]
        if str(item["article_id"]) in id:
            return item
        else:
            return {}

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        dict_of_keylists = {
            'figshare:shares' : ['shares'],
            'figshare:downloads' : ['downloads'],
            'figshare:views' : ['views']
        }
        item = self._extract_figshare_record(page, id)
        metrics_dict = provider._extract_from_data_dict(item, dict_of_keylists)
        return metrics_dict
