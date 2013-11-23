from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, re, os

import logging
logger = logging.getLogger('ti.providers.topsy')

class Topsy(Provider):  

    example_id = ("url", "http://total-impact.org")

    url = "http://www.topsy.com/"
    descr = "Real-time search for the social web, <a href='http://topsy.com'><img src='http://cdn.topsy.com/img/powered.png'/></a>"
    metrics_url_template = 'http://otter.topsy.com/stats.json?url=%s&apikey=' + os.environ["TOPSY_KEY"]
    provenance_url_template = 'http://topsy.com/trackback?url=%s'

    static_meta_dict =  {
        "tweets": {
            "display_name": "tweets",
            "provider": "Topsy",
            "provider_url": "http://www.topsy.com/",
            "description": "Number of times the item has been tweeted",
            "icon": "http://twitter.com/phoenix/favicon.ico",
        },    
        "influential_tweets": {
            "display_name": "influential tweets",
            "provider": "Topsy",
            "provider_url": "http://www.topsy.com/",
            "description": "Number of times the item has been tweeted by influential tweeters",
            "icon": "http://twitter.com/phoenix/favicon.ico" ,
        }
    }
    

    def __init__(self):
        super(Topsy, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return namespace in ["blog", "url"]

    def get_best_id(self, aliases):
        for alias in aliases:
            (namespace, nid) = alias
            if ("blog"==namespace):
                return nid
        #else
        return self.get_relevant_alias_with_most_metrics("topsy:tweets", aliases)

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


