from totalimpact.providers import provider
from totalimpact.providers import webpage
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, os, re

import logging
logger = logging.getLogger('ti.providers.blog_post')

class Blog_Post(Provider):  

    example_id = ("blog_post:retractionwatch.wordpress.com", u'http://retractionwatch.wordpress.com/2012/12/11/elsevier-editorial-system-hacked-reviews-faked-11-retractions-follow/')

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

    # overriding
    def biblio(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True): 
        logger.info(u"calling webpage to handle aliases")

        biblio_dict = self.webpage.biblio(aliases, provider_url_template, cache_enabled) 
        url = self.get_best_alias(aliases)

