from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.unicode_helpers import remove_nonprinting_characters

import os, re

import logging
logger = logging.getLogger('ti.providers.arxiv')

def clean_arxiv_id(arxiv_id):
    arxiv_id = remove_nonprinting_characters(arxiv_id)    
    arxiv_id = arxiv_id.lower().replace("arxiv:", "").replace("http://arxiv.org/abs/", "")
    return arxiv_id


class Arxiv(Provider):  

    example_id = ("arxiv", "1305.3328")

    url = "http://arxiv.org"
    descr = "arXiv is an e-print service in the fields of physics, mathematics, computer science, quantitative biology, quantitative finance and statistics."
    biblio_url_template = "http://export.arxiv.org/api/query?id_list=%s"
    aliases_url_template = "http://arxiv.org/abs/%s"

    static_meta_dict = {}


    def __init__(self):
        super(Arxiv, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if (namespace == "arxiv"):
            return True
        else:
            return False


    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    # overriding default because overriding member items method
    @property
    def provides_members(self):
        return True


    # overriding because don't need to look up
    def member_items(self, 
            query_dict, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_members:
            raise NotImplementedError()

        self.logger.debug(u"%s getting member_items for %s" % (self.provider_name, query_dict))

        arxiv_ids = query_dict.split("\n")
        aliases_tuples = [("arxiv", clean_arxiv_id(arxiv_id)) for arxiv_id in arxiv_ids if arxiv_id]

        return(aliases_tuples)


    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        arxiv_id = self.get_best_id(aliases)

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        new_alias = [("url", self._get_templated_url(provider_url_template, arxiv_id, "aliases"))]
        if new_alias in aliases:
            new_alias = []  #override because isn't new

        return new_alias


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['entry', 'title'],
            'date' : ['entry', 'published'],
        }
        biblio_dict = provider._extract_from_xml(page, dict_of_keylists)
        dom_authors = provider._find_all_in_xml(page, "name")

        try:
            authors = [author.firstChild.data for author in dom_authors]
            biblio_dict["authors"] = ", ".join([author.split(" ")[-1] for author in authors])
        except (AttributeError, TypeError):
            pass

        try:
            biblio_dict["year"] = biblio_dict["date"][0:4]
        except KeyError:
            pass

        biblio_dict["repository"] = "arXiv"
        biblio_dict["free_fulltext_url"] = self._get_templated_url(self.aliases_url_template, id, "aliases")

        return biblio_dict    
       


