from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import logging
logger = logging.getLogger('providers.webpage')

class Webpage(Provider):  

    metric_names = []

    biblio_url_template = "%s"
    provenance_url_template = "%s"

    example_id = ("url", "http://total-impact.org/")

    def __init__(self):
        super(Webpage, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("url" == namespace)


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['html', 'head', 'title'],
            'h1' : ['h1']
        }
        biblio_dict = provider._extract_from_xml(page, dict_of_keylists)
        return biblio_dict    
