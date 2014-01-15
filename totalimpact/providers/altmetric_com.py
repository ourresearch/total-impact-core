from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import json, re, os
from operator import itemgetter

import logging
logger = logging.getLogger('ti.providers.altmetric_com')

class Altmetric_Com(Provider):  

    example_id = ("doi", "10.1101/gr.161315.113")

    url = "http://www.altmetric.com"
    descr = "We make article level metrics easy."
    aliases_url_template = 'http://api.altmetric.com/v1/fetch/%s?key=' + os.environ["ALTMETRIC_COM_KEY"]
    metrics_url_template = 'http://api.altmetric.com/v1/fetch/%s?key=' + os.environ["ALTMETRIC_COM_KEY"]
    provenance_url_template = 'http://www.altmetric.com/details.php?citation_id=%s&src=impactstory.org'

    static_meta_dict =  {
        "tweets": {
            "display_name": "tweets",
            "provider": "Altmetric.com",
            "provider_url": "http://www.altmetric.com",
            "description": "Number of times the product has been tweeted",
            "icon": "http://www.altmetric.com/favicon.ico",
        }
    }
    

    def __init__(self):
        super(Altmetric_Com, self).__init__()

    @property
    def provides_aliases(self):
        return True

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return namespace in ["doi"]

    def get_best_id(self, aliases):
        # return it with the id type as a prefix before / because that's how the altmetric.com api expects it
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "doi" in aliases_dict:
            best_id = "doi/{id}".format(id=aliases_dict["doi"][0])
        elif "pmid" in aliases_dict:
            best_id = "pmid/{id}".format(id=aliases_dict["pmid"][0])
        elif "arxiv" in aliases_dict:
            best_id = "arxiv_id/{id}".format(id=aliases_dict["arxiv"][0])
        elif "altmetric_com" in aliases_dict:
            best_id = "altmetric_com/{id}".format(id=aliases_dict["altmetric_com"][0])
        else:
            best_id = None
        return(best_id)


    def provenance_url(self, metric_name, aliases):
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        try:
            drilldown_url = self._get_templated_url(self.provenance_url_template, aliases_dict["altmetric_com"][0])
        except KeyError:
            drilldown_url = ""
        return drilldown_url

    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        aliases_dict = provider.alias_dict_from_tuples(aliases)
        print "looking for aliases for", aliases

        if "altmetric_com" in aliases_dict:
            print "already have one"
            return []  # nothing new to add

        nid = self.get_best_id(aliases)
        print "best nid", nid
        if not nid:
            return []

        new_aliases = self._get_aliases_for_id(nid, provider_url_template, cache_enabled)
        return new_aliases


    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"altmetric_com": ["altmetric_id"]}

        aliases_dict = provider._extract_from_json(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [("altmetric_com", str(aliases_dict["altmetric_com"]))]
        else:
            aliases_list = []
        return aliases_list


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        dict_of_keylists = {
            'altmetric_com:tweets' : ['counts', 'twitter', 'posts_count']
        }
        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict




