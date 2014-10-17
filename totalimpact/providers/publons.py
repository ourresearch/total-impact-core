from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os, re

import logging
logger = logging.getLogger('ti.providers.publons')

class Publons(Provider):  

    example_id = ("url", "egonw,cdk")

    url = "https://publons.com/"
    descr = "Speeding up science by making peer review faster, more efficient, and more effective."
    member_items_url_template = u"https://publons.com/api/v1/author/%s/"
    aliases_url_template = u"https://publons.com/api/v1/review/%s/"
    biblio_url_template = u"https://publons.com/api/v1/review/%s/"
    metrics_url_template = u"https://publons.com/api/v1/review/%s/"
    provenance_url_template = u"https://publons.com/review/%s/" 

    static_meta_dict = {
        "stars": {
            "display_name": "stars",
            "provider": "GitHub",
            "provider_url": "http://github.com",
            "description": "The number of people who have given the GitHub repository a star",
            "icon": "https://github.com/fluidicon.png",
        },
        "forks": {
            "display_name": "forks",
            "provider": "GitHub",
            "provider_url": "http://github.com",
            "description": "The number of people who have forked the GitHub repository",
            "icon": "https://github.com/fluidicon.png",
            }
    }     

    def __init__(self):
        super(Publons, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = ((namespace=="url") and ("publons.com/" in nid))
        return(relevant)

    #override because need to break up id
    def _get_templated_url(self, template, input_url, method=None):
        url = None
        try:
            if method=="members":
                match = re.match("^https://publons.com/author/(\d+)/.+", input_url)
                user_id = match.group(1)
                url = template % user_id
            else:
                match = re.match("^https://publons.com/r.*/(\d+).*", input_url)
                review_id = match.group(1)
                url = template % review_id
        except AttributeError:
            pass

        return(url)

    def _extract_members(self, page, account_name): 
        members = []
        # add repositories from account
        data = provider._load_json(page)
        review_urls = [review["_id"]["url"] for review in data["reviews"] 
                            if review["title"]!="An undisclosed article"]
        members += [("url", url) for url in review_urls]

        return(members)

    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"doi": ["doi"]}

        aliases_dict = provider._extract_from_json(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list

    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['title'],
            'authors' : ['author', 'last_name'],
            'journal' : ['source', 'provider'],
            'review_url' : ['source', 'url'],
            'review_type' : ['review_type'],
            'create_date' : ['datetime_reviewed'],
            'free_fulltext_url' : ['_id', 'url'],
            'source_provider' : ['source', 'provider'],
            'source_url' : ['source', 'url']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)
        biblio_dict["genre"] = "peer review"
        biblio_dict["title"] = "Review of " + biblio_dict["title"]

        if "source_provider" in biblio_dict and biblio_dict["source_provider"]:
            biblio_dict["repository"] = biblio_dict["source_provider"]
        else:
            biblio_dict["repository"] = "Publons"

        if "source_url" in biblio_dict and biblio_dict["source_url"]:
            biblio_dict["free_fulltext_url"] = biblio_dict["source_url"]  #overwrite with original source

        try:
            biblio_dict["year"] = biblio_dict["create_date"][0:4]
        except KeyError:
            pass

        return biblio_dict    
       
    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "views" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'publons:views' : ['stats', 'views']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict

