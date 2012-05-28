from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import BeautifulSoup

import logging
logger = logging.getLogger('providers.crossref')

class Crossref(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")
    url = "http://www.crossref.org/"
    descr = "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."
    biblio_url_template = None  #set in init
    aliases_url_template = None  #set in init

    def __init__(self):
        super(Crossref, self).__init__()
        common_url_template = "http://doi.crossref.org/servlet/query?pid=" + self.tool_email + "&qdata=%s&format=unixref"
        self.biblio_url_template = common_url_template
        self.aliases_url_template = common_url_template


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['doi_record', 'title'],
            'year' : ['doi_record', 'year'],
            'journal' : ['doi_record', 'abbrev_title'],
        }
        biblio_dict = provider._extract_from_xml(page, dict_of_keylists)

        soup = BeautifulSoup.BeautifulStoneSoup(page) 
        if not soup:
            raise(ProviderContentMalformedError)

        authors_list = soup.findAll(contributor_role="author")
        authors = ", ".join([str(author.surname.text) for author in authors_list if author.surname])
        if authors:
            biblio_dict["authors"] = authors

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"url": ["doi_record", "doi_data", "resource"], 
                            "title" : ["doi_record", "title"]}

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)

        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list

