from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import lxml.html

import logging
logger = logging.getLogger('providers.webpage')

class Webpage(Provider):  

    example_id = ("url", "http://total-impact.org/")

    biblio_url_template = "%s"
    provenance_url_template = "%s"
    descr = "Information scraped from webpages by total-impact"
    url = "http://total-impact.org"


    def __init__(self):
        super(Webpage, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("url" == namespace)


    # use lxml because is html
    def _extract_biblio(self, page, id=None):
        #dict_of_keylists = {
        #    'title' : ['html', 'head', 'title'],
        #    'h1' : ['h1']
        #}

        parsed_html = lxml.html.document_fromstring(page.encode("utf-8"))
        title = parsed_html.find(".//title").text
        h1 = parsed_html.find(".//h1").text

        biblio_dict = {}
        if title:
            biblio_dict["title"] = title
        if h1:
            biblio_dict["h1"] = h1

        return biblio_dict    
