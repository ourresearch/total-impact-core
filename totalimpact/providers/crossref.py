from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import BeautifulSoup

import logging
logger = logging.getLogger('ti.providers.crossref')

#!/usr/bin/env python

import httplib, urllib, re

class Crossref(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")
    url = "http://www.crossref.org/"
    descr = "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."
    aliases_url_template = "http://dx.doi.org/%s"
    biblio_url_template = "http://dx.doi.org/%s"
    # example code to test 
    # curl -D - -L -H   "Accept: application/vnd.citationstyles.csl+json" "http://dx.doi.org/10.1021/np070361t" 

    def __init__(self):
        super(Crossref, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)

    @property
    def provides_aliases(self):
         return True

    # default method; providers can override
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug("%s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider        
        response = self.http_get(url, 
            cache_enabled=cache_enabled, 
            allow_redirects=True,
            headers={"Accept": "application/vnd.citationstyles.csl+json"})

        if response.status_code != 200:
            self.logger.info("%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404: #not found
                return {}
            elif response.status_code == 403: #forbidden
                return {}
            elif ((response.status_code >= 300) and (response.status_code < 400)): #redirect
                return {}
            else:
                self._get_error(response.status_code, response)


        # extract the aliases
        try:
            response.encoding = "utf-8"
            biblio_dict = self._extract_biblio(response.text, id)
        except (AttributeError, TypeError):
            biblio_dict = {}

        return biblio_dict

    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['title'],
            'year' : ['issued'],
            'repository' : ['publisher'],
            'journal' : ['container-title'],
            'authors_literal' : ['author']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)
        if not biblio_dict:
          return {}

        try:
            surname_list = [author["family"] for author in biblio_dict["authors_literal"]]
            if surname_list:
                biblio_dict["authors"] = ", ".join(surname_list)
                del biblio_dict["authors_literal"]
        except (IndexError, KeyError):
            try:
                literal_list = [author["literal"] for author in biblio_dict["authors_literal"]]
                if literal_list:
                    biblio_dict["authors_literal"] = "; ".join(literal_list)
            except (IndexError, KeyError):
                pass

        try:
            if "year" in biblio_dict:
                if "raw" in biblio_dict["year"]:
                    biblio_dict["year"] = biblio_dict["year"]["raw"]
                elif "date-parts" in biblio_dict["year"]:
                    biblio_dict["year"] = biblio_dict["year"]["date-parts"][0][0]
        except IndexError:
            logger.info("could not parse year {biblio_dict}".format(
                biblio_dict=biblio_dict))
            del biblio_dict["year"]
            pass

        # replace many white spaces and \n with just one space
        try:
            biblio_dict["title"] = re.sub(u"\s+", u" ", biblio_dict["title"])
        except KeyError:
            pass

        return biblio_dict  


    # overriding default
    def _get_aliases_for_id(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug("%s getting aliases for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        url = self._get_templated_url(provider_url_template, id, "aliases")

        # add url for http://dx.doi.org/
        # disable for now, till providers can handle multiple urls
        #new_aliases = [("url", url)] # adds http://dx.doi.org/ url
        new_aliases = []

        # add biblio
        biblio_dict = self.biblio([("doi", id)])
        if biblio_dict:
            new_aliases += [("biblio", biblio_dict)]

        # try to get the redirect as well
        response = self.http_get(url, cache_enabled=cache_enabled, allow_redirects=True)

        if response.status_code >= 400:
            self.logger.info("%s http_get status code=%i" 
                % (self.provider_name, response.status_code))
            raise provider.ProviderServerError("doi resolve")

        try:       
            new_aliases += [("url", response.url)]
        except (TypeError, AttributeError):
            pass

        return new_aliases

