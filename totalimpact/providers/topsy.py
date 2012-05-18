from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from secrets import Topsy_key

import simplejson
import re

import logging
logger = logging.getLogger('providers.topsy')

class Topsy(Provider):  

    metric_names = [
        'topsy:tweets', 
        'topsy:influential_tweets'
        ]

    metrics_url_template = "http://otter.topsy.com/stats.json?url=%s&apikey=" + Topsy_key
    provenance_url_template = "http://topsy.com/%s/?utm_source=otter"

    example_id = ("url", "http://total-impact.org")

    def __init__(self):
        super(Topsy, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("url" == namespace)


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        dict_of_keylists = {
            'topsy:tweets' : ['response', 'all'],
            'topsy:influential_tweets' : ['response', 'influential']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict

    # overriding default because needs to strip off the http: before inserting
    def provenance_url(self, metric_name, aliases):
        # Returns the same provenance url for all metrics
        id = self.get_best_id(aliases)

        if not id:
            return None

        base_id = re.sub(r"^http://", '', id)
        if not base_id:
            provenance_url = None

        provenance_url = self._get_templated_url(self.provenance_url_template, base_id, "provenance")
        return provenance_url


