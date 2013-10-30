from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import hashlib
import urllib

import logging
logger = logging.getLogger('ti.providers.delicious')

class Delicious(Provider):  

    example_id = ("url", "http://total-impact.org")
    metrics_url_template = "http://feeds.delicious.com/v2/json/url/%s?count=100"
    provenance_url_template = "http://delicious.com/link/%s"
    url = "http://www.delicious.com"
    descr = "Online social bookmarking service"
    static_meta_dict = {
        "bookmarks": {
            "display_name": "bookmarks",
            "provider": "Delicious",
            "provider_url": "http://www.delicious.com/",
            "description": "The number of bookmarks to this artifact (maximum=100).",
            "icon": "http://g.etfv.co/http://delicious.com"  #couldn't figure out link for local favicon
        }
    }

    def __init__(self):
        super(Delicious, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("url" == namespace)

    def get_best_id(self, aliases):
        return self.get_relevant_alias_with_most_metrics("delicious:bookmarks", aliases)

    # overriding default because delicious needs md5 of url in template
    def _get_templated_url(self, template, id, method=None):
        try:
            id_unicode = unicode(id, "UTF-8")
        except TypeError:
            id_unicode = id
        id_utf8 = id_unicode.encode("UTF-8")
        md5_of_url = hashlib.md5(id_utf8).hexdigest()
        url = template % md5_of_url
        return(url)

    def _extract_metrics(self, page, status_code=200, id=None):
        metrics_dict = {}
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        data = provider._load_json(page)
        number_of_bookmarks = len(data)
        if number_of_bookmarks:
            metrics_dict = {
                'delicious:bookmarks' : number_of_bookmarks
            }

        return metrics_dict

    def provenance_url(self, metric_name, aliases):
        # Returns the same provenance url for all metrics
        id = self.get_best_id(aliases)

        if not id:
            return None

        # first we need to get a user, by looking up metrics again
        url = self._get_templated_url(self.provenance_url_template, id, "provenance")

        return url



