from totalimpact.providers import provider
from totalimpact.providers import webpage
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderServerError

import json, os, re

import logging
logger = logging.getLogger('ti.providers.blog_post')

class Blog_Post(Provider):  

    example_id = ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "researchremix.wordpress.com"}')

    provenance_url_template = "%s"

    static_meta_dict = {}

    def __init__(self):
        super(Blog_Post, self).__init__()
        self.webpage = webpage.Webpage()


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return "blog_post" in namespace


    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    # overriding default because overriding aliases method
    @property
    def provides_biblio(self):
        return True
  

    def post_url_from_nid(self, nid):
        return json.loads(nid)["post_url"]    
  
    def blog_url_from_from_nid(self, nid):
        return json.loads(nid)["blog_url"]    


    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        new_aliases = []

        for alias in aliases:
            if self.is_relevant_alias(alias):
                (namespace, nid) = alias
                new_alias = ("url", self.post_url_from_nid(nid))
                if new_alias not in aliases:
                    new_aliases += [new_alias]

        return new_aliases

    # overriding
    def biblio(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True): 
        logger.info(u"calling webpage to handle aliases")

        nid = self.get_best_id(aliases)

        biblio_dict = self.webpage.biblio([("url", self.post_url_from_nid(nid))], provider_url_template, cache_enabled) 
        biblio_dict["url"] = self.post_url_from_nid(nid)
        biblio_dict["account"] = self.blog_url_from_from_nid(nid)
        if ("title" in biblio_dict) and ("|" in biblio_dict["title"]):
            (title, blog_title) = biblio_dict["title"].rsplit("|", 1)
            biblio_dict["title"] = title.strip()
            biblio_dict["blog_title"] = blog_title.strip()

        return biblio_dict

