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

    #override because need to add "doi:" prefix when necessary
    def _get_templated_url(self, template, id, method=None):
        if id.startswith("10."):
            id = "doi:" + id
        url = template % id
        return(url)

    def _extract_biblio(self, redirect_page, id=None):
        redirect_dict_of_keylists = {
            'url' : ['url']
        }

        redirect_dict = provider._extract_from_xml(redirect_page, redirect_dict_of_keylists)

        logger.info(u"%20s WARNING, url= %s" 
                % (self.provider_name, redirect_dict["url"]))            

        # try to get a response from the data provider        
        response = self.http_get(redirect_dict["url"])

        if response.status_code != 200:
            logger.warning(u"%20s WARNING, status_code=%i getting %s" 
                % (self.provider_name, response.status_code, url))            
            self._get_error(response.status_code, response)
            return {}

        dict_of_keylists = {
            'title' : ['dataset', 'title'], 
            'published_date' : ['dataset', 'pubDate']
        }
        biblio_dict = provider._extract_from_xml(response.text, dict_of_keylists)

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {
            'url' : ['url']
        }

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)

        try:
            doi = provider.doi_from_url_string(aliases_dict["url"])
            if doi:
                aliases_dict["doi"] = doi
        except KeyError:
            pass

        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list

