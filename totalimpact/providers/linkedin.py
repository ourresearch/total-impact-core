import os, re, requests
from bs4 import BeautifulSoup

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderRateLimitError

import logging
logger = logging.getLogger('ti.providers.linkedin')

class Linkedin(Provider):  

    example_id = ("url", "https://www.linkedin.com/in/heatherpiwowar")
    url = "http://www.crossref.org/"
    descr = "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."
    aliases_url_template = "http://dx.doi.org/%s"
    biblio_url_template = "http://dx.doi.org/%s"
 

    def __init__(self):
        super(Linkedin, self).__init__()


    @property
    def provides_members(self):
        return True

    @property
    def provides_biblio(self):
         return True

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if (namespace == "url") and ("linkedin.com" in nid):
            return True
        return False


    def member_items(self, 
            linkedin_url, 
            provider_url_template=None, 
            cache_enabled=True):
        return [("url", linkedin_url)]

    @property
    def provides_aliases(self):
         return True

    @property
    def provides_biblio(self):
         return True


    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True): 
        return None 


    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        linkedin_url = self.get_best_id(aliases)
        biblio_dict = {}
        biblio_dict["repository"] = "LinkedIn"
        biblio_dict["is_account"] = True  # special key to tell webapp to render as genre heading
        biblio_dict["genre"] = "account"
        biblio_dict["account"] = linkedin_url

        try:
            r = requests.get(linkedin_url, timeout=20)
        except requests.exceptions.Timeout:
            return None        
        soup = BeautifulSoup(r.text)
        try:
            bio = soup.find("p", {'class': "description"}).get_text() #because class is reserved
            biblio_dict["bio"] = bio
        except AttributeError:
            logger.warning("AttributeError in linkedin")
            logger.warning(r.text)

        return biblio_dict
  


