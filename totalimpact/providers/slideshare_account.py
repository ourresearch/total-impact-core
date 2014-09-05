from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderItemNotFoundError, ProviderRateLimitError

import simplejson, urllib, time, hashlib, re, os
from xml.dom import minidom 
from xml.parsers.expat import ExpatError

import logging
logger = logging.getLogger('ti.providers.slideshare_account')

class Slideshare_Account(Provider):  

    example_id = ("url", "http://www.slideshare.net/cavlec")
    url = "http://www.slideshare.net/"
    descr = "The best way to share presentations, documents and professional videos."

    biblio_url_template = u"%s/followers"
    metrics_url_template = u"%s/followers"
    provenance_url_template = u"%s/followers"

    static_meta_dict = {
        "followers": {
            "display_name": "followers",
            "provider": "SlideShare",
            "provider_url": "http://www.slideshare.net/",
            "description": "The number of people who follow this account",
            "icon": "http://www.slideshare.net/favicon.ico" ,
        }  
    }


    def __init__(self):
        super(Slideshare_Account, self).__init__()

    @property
    def provides_biblio(self):
         return True

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if (namespace != "url"):
            return False
        if re.match(".+slideshare.net/.+/.+", nid):
            return False
        if re.match(".+slideshare.net/.+", nid):
            return True
        return False

    def _get_templated_url(self, template, id, method=None):
        try:
            id_unicode = unicode(id, "UTF-8")
        except TypeError:
            id_unicode = id
        id_utf8 = id_unicode.encode("UTF-8")
        substitute_id = id_utf8
        url = template % substitute_id
        return(url)

    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True): 

        id = self.get_best_id(aliases)
                   
        biblio_dict = {}
        biblio_dict["repository"] = "SlideShare"
        biblio_dict["is_account"] = True
        biblio_dict["genre"] = "account"
        biblio_dict["account"] = id
        return biblio_dict    


    def _extract_metrics(self, page, status_code=200, id=None):
        logger.info("in slideshare_account, _extract_metrics with id {id}".format(
            id=id))

        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        metrics_dict = {}
        match = re.search("(\d+) Followers", page)

        try:
            followers = int(match.group(1))
            if followers:
                metrics_dict = {"slideshare_account:followers": followers}
        except (AttributeError, TypeError):
            pass

        return metrics_dict

