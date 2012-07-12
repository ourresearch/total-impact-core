from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson

import logging
logger = logging.getLogger('ti.providers.dataone')

class Dataone(Provider):  

    example_id = ("dataone", "esa.44.1")

    url = "http://www.dataone.org"
    descr = "Cyberinfrastructure for new innovative environmental science"
    biblio_url_template = "https://cn.dataone.org/cn/v1/resolve/%s"
    aliases_url_template = "https://cn.dataone.org/cn/v1/resolve/%s"

    def __init__(self):
        super(Dataone, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("dataone" == namespace)

    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['dataset', 'title'], 
            'published_date' : ['dataset', 'pubDate']
        }
        biblio_dict = provider._extract_from_xml(page, dict_of_keylists)

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {
            'url' : ['url']
        }

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)

        try:
            aliases_dict["doi"] = provider.doi_from_url_string(aliases_dict["url"])
        except KeyError:
            pass

        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list

