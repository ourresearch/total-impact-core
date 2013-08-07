from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson
import re

import logging
logger = logging.getLogger('providers.facebook')

class Facebook(Provider):  

    example_id = ("url", "http://total-impact.org")

    url = "http://www.facebook.com/"
    descr = "A social networking service."
    metrics_url_template = "http://api.facebook.com/restserver.php?method=links.getStats&urls=%s"
    provenance_url_template = ""

    static_meta_dict =  {
        "likes": {
            "display_name": "likes",
            "provider": "Facebook",
            "provider_url": "http://www.facebook.com/",
            "description": "Number of users who Liked a post about the item",
            "icon": "http://www.facebook.com/favicon.ico" ,
        },    
        "shares": {
            "display_name": "shares",
            "provider": "Facebook",
            "provider_url": "http://www.facebook.com/",
            "description": "Number of users who shared a post about the item",
            "icon": "http://www.facebook.com/favicon.ico" ,
        },    
        "comments": {
            "display_name": "comments",
            "provider": "Facebook",
            "provider_url": "http://www.facebook.com/",
            "description": "Number of users who commented on a post about the item",
            "icon": "http://www.facebook.com/favicon.ico" ,
        },    
        "clicks": {
            "display_name": "clicks",
            "provider": "Facebook",
            "provider_url": "http://www.facebook.com/",
            "description": "Number of users who clicked on a post about the item",
            "icon": "http://www.facebook.com/favicon.ico" ,
        }    
    }
    

    def __init__(self):
        super(Facebook, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("url" == namespace)

    def get_best_id(self, aliases):
        return self.get_relevant_alias_with_most_metrics("facebook:likes", aliases)

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "links_getStats_response" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'facebook:likes' : ['like_count'],
            'facebook:shares' : ['share_count'],
            'facebook:comments' : ['comment_count'],
            'facebook:clicks' : ['click_count']
        }

        metrics_dict = provider._extract_from_xml(page, dict_of_keylists)

        return metrics_dict

    def provenance_url(self, metric_name, aliases):
        # facebook has no provenance_url
        return ""


