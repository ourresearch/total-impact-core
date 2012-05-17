from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from secrets import Topsy_key

import simplejson

import logging
logger = logging.getLogger('providers.github')

class Topsy(Provider):  

    metric_names = [
        'topsy:tweets', 
        'topsy:influential_tweeets'
        ]

    metrics_url_template = "http://otter.topsy.com/stats.json?url=%s&apikey=" + Topsy_key
    provenance_url_template ="temp%s"

    example_id = ("url", "http://total-impact.org")

    def __init__(self):
        super(Github, self).__init__()

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
            'topsy:influential_tweeets' : ['response', 'influential']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict


