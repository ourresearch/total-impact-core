from totalimpact.providers import provider
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


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        is_figshare_doi = (namespace == "doi") and (".figshare." in nid.lower())
        return is_figshare_doi

    def _extract_item(self, page, id):
        data = provider._load_json(page)
        if not data:
            return {}
        item = data["items"][0]
        if item["doi"] == self._get_templated_url(self.provenance_url_template, id, "provenance"):
            return item
        else:
            return {}


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['title'],
            'authors' : ['authors'],
            'published_date' : ['published_date'],
            'url' : ['doi']
        }
        item = self._extract_item(page, id)
        biblio_dict = provider._extract_from_data_dict(item, dict_of_keylists)

        if "published_date" in biblio_dict:
            biblio_dict["year"] = biblio_dict["published_date"][-4:]
            del biblio_dict["published_date"]
        if "authors" in biblio_dict:
            biblio_dict["authors"] = ", ".join(author["last_name"] for author in biblio_dict["authors"])

        biblio_dict["repository"] = "figshare"

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {
            'title' : ['title'],
            'url' : ['doi']
        }
        item = self._extract_item(page, id)
        aliases_dict = provider._extract_from_data_dict(item, dict_of_keylists)

        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list


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
        item = self._extract_item(page, id)
        metrics_dict = provider._extract_from_data_dict(item, dict_of_keylists)
        return metrics_dict
