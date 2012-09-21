from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, re, os

import logging
logger = logging.getLogger('ti.providers.topsy')

class Topsy(Provider):  

    example_id = ("url", "http://total-impact.org")

    url = "http://www.topsy.com/"
    descr = "Real-time search for the social web, <a href='http://topsy.com'><img src='http://cdn.topsy.com/img/powered.png'/></a>"
    metrics_url_template = 'http://otter.topsy.com/stats.json?url="%s"&apikey=' + os.environ["TOPSY_KEY"]
    provenance_url_template = 'http://topsy.com/%s?utm_source=otter'

    static_meta_dict =  {
        "tweets": {
            "display_name": "tweets",
            "provider": "Topsy",
            "provider_url": "http://www.topsy.com/",
            "description": "Number of times the item has been tweeted",
            "icon": "http://twitter.com/phoenix/favicon.ico" ,
        },    
        "influential_tweets": {
            "display_name": "influencial tweets",
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


