from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, os

import logging
logger = logging.getLogger('ti.providers.wordpresscom')

class Wordpresscom(Provider):  

    example_id = ("blog", "http://blog.impactstory.org")

    url = "http://wordpress.com"
    descr = "A blog web hosting service provider owned by Automattic, and powered by the open source WordPress software."
    biblio_url_template = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    metrics_url_template = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    provenance_url_template = "%s"

    static_meta_dict = {
        "subscribers": {
            "display_name": "subscribers",
            "provider": "WordPress.com",
            "provider_url": "http://wordpress.com",
            "description": "The number of people who have subscribed to this blog on WordPress.com",
            "icon": "https://wordpress.com/favicon.ico",
        }
    }     

    def __init__(self):
        super(Wordpresscom, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return "blog"==namespace

    # overriding default because overriding member_items method
    @property
    def provides_members(self):
        return True

    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    #override because need to break up id
    def _get_templated_url(self, template, nid, method=None):
        if method in ["metrics", "biblio"]:
            nid = nid.replace("http://", "")
        url = template % (nid)
        return(url)


    # overriding
    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        members = [("blog", url) for url in query_string.split("\n")]
        return (members)

  
    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        new_aliases = []

        for alias in aliases:
            if self.is_relevant_alias(alias):
                (namespace, nid) = alias
                new_alias = ("url", nid)
                if new_alias not in aliases:
                    new_aliases += [new_alias]

        return new_aliases


    def _extract_biblio(self, page, id=None):
        if not "is_private" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'title' : ['name'],
            'description' : ['description']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)
        biblio_dict["url"] = id

        return biblio_dict         

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "is_private" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'wordpresscom:subscribers' : ['subscribers_count']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict