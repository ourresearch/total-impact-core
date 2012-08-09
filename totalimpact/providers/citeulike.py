from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson
import re

import logging
logger = logging.getLogger('providers.citeulike')

class Citeulike(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.citeulike.org/"
    descr = "CiteULike is a free service to help you to store, organise and share the scholarly papers you are reading."
    metrics_url_template = "http://www.citeulike.org/api/posts/for/doi/%s"
    provenance_url_template = "http://www.citeulike.org/doi/%s"

    static_meta_dict =  {
        "bookmarks": {
            "display_name": "bookmarks",
            "provider": "CiteULike",
            "provider_url": "http://www.citeulike.org/",
            "description": "Number of users who have bookmarked this item.",
            "icon": "http://citeulike.org/favicon.ico" ,
        }    
    }
    

    def __init__(self):
        super(Citeulike, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not provider._count_in_xml(page, 'posts'):
            raise ProviderContentMalformedError

        count = provider._count_in_xml(page, 'post')
        if count:
            metrics_dict = {'citeulike:bookmarks': count}
        else:
            metrics_dict = {}

        return metrics_dict



