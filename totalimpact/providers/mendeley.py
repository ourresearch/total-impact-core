from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers.secrets import Mendeley_key

import simplejson, urllib

import logging
logger = logging.getLogger('providers.mendeley')

class Mendeley(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.mendeley.com"
    descr = " A research management tool for desktop and web."
    everything_url_template = "http://api.mendeley.com/oapi/documents/details/%s?type=doi&consumer_key=" + Mendeley_key
    biblio_url_template = everything_url_template
    aliases_url_template = everything_url_template
    metrics_url_template = everything_url_template
    provenance_url_template = everything_url_template

    static_meta_dict = {
        "readers": {
            "display_name": "readers",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "The number of readers who have added the article to their libraries",
            "icon": "http://www.mendeley.com/favicon.ico",
        },    
        "groups": {
            "display_name": "groups",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "The number of groups who have added the article to their libraries",
            "icon": "http://www.mendeley.com/favicon.ico",
        }
    }


    def __init__(self):
        super(Mendeley, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (namespace=="doi" or namespace=="pmid")
        return(relevant)

    #override because need to break up id
    def _get_templated_url(self, template, id, method=None):
        double_encoded_id = urllib.quote(urllib.quote(id, safe=""), safe="")
        query_url = template % double_encoded_id    
        return(query_url)


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['title'],
            'year' : ['year'],
            'journal' : ['publication_outlet'],
            'authors' : ["authors"]
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)

        # return authors as a string of last names
        try:
            author_list = biblio_dict["authors"]
            author_string = ", ".join([author["surname"] for author in author_list])
            if author_string:
                biblio_dict["authors"] = author_string
        except TypeError:
            pass

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"url": ["website"], 
                            "title" : ["title"]}

        aliases_dict = provider._extract_from_json(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        dict_of_keylists = {"mendeley:readers": ["stats", "readers"], 
                            "mendeley:groups" : ["groups"]}

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        # get count of groups
        try:
            metrics_dict["mendeley:groups"] = len(metrics_dict["mendeley:groups"])
        except (TypeError, KeyError):
            # don't add null or zero metrics
            pass

        return metrics_dict


    # default method; providers can override    
    def provenance_url(self, metric_name, aliases):

        id = self.get_best_id(aliases)     
        if not id:
            # not relevant to Mendeley
            return None

        url = self._get_templated_url(self.provenance_url_template, id, "provenance")

        logger.debug("attempting to retrieve provenance url from " + url)
        # try to get a response from the data provider        
        response = self.http_get(url)
        if response.status_code != 200:
            # not in Mendeley database
            return []

        page = response.text
        data = provider._load_json(page)
        provenance_url = data['mendeley_url']
        return provenance_url
