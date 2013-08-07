from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError
import BeautifulSoup, itertools

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

        self.logger.debug(u"%s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = provider_url_template % id

        biblio_dict = self._lookup_biblio_from_doi(id, url, cache_enabled)

        return biblio_dict


    def _lookup_biblio_from_doi(self, id, url, cache_enabled):
        # try to get a response from the data provider        
        response = self.http_get(url, 
            cache_enabled=cache_enabled, 
            allow_redirects=True,
            headers={"Accept": "application/vnd.citationstyles.csl+json"})

        if response.status_code != 200:
            self.logger.info(u"%s status_code=%i" 
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
                    biblio_dict["year"] = str(biblio_dict["year"]["raw"])
                elif "date-parts" in biblio_dict["year"]:
                    biblio_dict["year"] = str(biblio_dict["year"]["date-parts"][0][0])
        except IndexError:
            logger.info(u"could not parse year {biblio_dict}".format(
                biblio_dict=biblio_dict))
            del biblio_dict["year"]
            pass

        # replace many white spaces and \n with just one space
        try:
            biblio_dict["title"] = re.sub(u"\s+", u" ", biblio_dict["title"])
        except KeyError:
            pass

        return biblio_dict  


    #overriding default
    # if no doi, try to get doi from biblio
    # after that, if doi, get url and biblio
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        aliases_dict = provider.alias_dict_from_tuples(aliases)

        if "doi" in aliases_dict:
            doi = aliases_dict["doi"][0]
        else:
            doi = None

        new_aliases = []
        if not doi:
            if "biblio" in aliases_dict:
                doi = self._lookup_doi_from_biblio(aliases_dict["biblio"][0], cache_enabled)
                if doi:
                    new_aliases += [("doi", doi)]   
                else:
                    if "url" in aliases_dict["biblio"][0]:
                        new_aliases += [("url", aliases_dict["biblio"][0]["url"])] 

        if not doi:
            # nothing else we can do 
            return new_aliases  #urls if we have them, otherwise empty list

        new_aliases += self._lookup_urls_from_doi(doi, provider_url_template, cache_enabled)
        
        # get uniques for things that are unhashable
        new_aliases_unique = [k for k,v in itertools.groupby(sorted(new_aliases))]
        return new_aliases_unique

    def _lookup_doi_from_biblio(self, biblio, cache_enabled):
        if not biblio:
            return []

        try:
            if (biblio["journal"] == ""):
                # need to have journal or can't look up with current api call
                logger.info(u"%20s NO DOI because no journal in %s" % (
                    self.provider_name, biblio))
                return []
            query_string =  ("|%s|%s|%s|%s|%s|%s||%s|" % (
                biblio.get("journal", ""),
                biblio.get("first_author", biblio.get("authors", "").split(",")[0].strip()),
                biblio.get("volume", ""),
                biblio.get("number", ""),
                biblio.get("first_page", ""),
                biblio.get("year", ""),
                "ImpactStory"
                ))
        except KeyError:
            logger.info(u"%20s NO DOI because missing needed attribute in %s" % (
                self.provider_name, biblio))
            return []


        # for more info on crossref spec, see
        # http://ftp.crossref.org/02publishers/25query_spec.html
        url = "http://doi.crossref.org/servlet/query?pid=totalimpactdev@gmail.com&qdata=%s" % query_string

        try:
            logger.debug(u"%20s calling crossref at %s" % (self.provider_name, url))
            # doi-lookup call to crossref can take a while, give it a long timeout
            response = self.http_get(url, timeout=30, cache_enabled=cache_enabled)
        except ProviderTimeout:
            raise ProviderTimeout("CrossRef timeout")

        if response.status_code != 200:
            raise ProviderServerError("CrossRef status code was not 200")

        if not biblio["journal"].lower() in response.text.lower():
            raise ProviderServerError("CrossRef returned invalid text response")

        response_lines = response.text.split("\n")

        split_lines = [line.split("|") for line in response_lines if line]
        line_keys = [line[-2].strip() for line in split_lines]
        dois = [line[-1].strip() for line in split_lines]

        for key, doi in zip(line_keys, dois):
            if not doi:
                try:
                    logger.debug(u"%20s NO DOI from %s, %s" %(self.provider_name, biblio, key))
                except KeyError:
                    logger.debug(u"%20s NO DOI from %s, %s" %(self.provider_name, "", key))                    

        return doi


    # overriding default
    # gets url and biblio from doi
    def _lookup_urls_from_doi(self, 
            doi, 
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug(u"%s getting aliases for %s" % (self.provider_name, doi))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template
        # make it this way because don't want escaping
        doi_url = provider_url_template % doi

        # add url for http://dx.doi.org/ without escaping
        new_aliases = [("url", doi_url)]

        # add biblio
        biblio_dict = self.biblio([("doi", doi)])
        if biblio_dict:
            new_aliases += [("biblio", biblio_dict)]

        # try to get the redirect as well
        response = self.http_get(doi_url, cache_enabled=cache_enabled, allow_redirects=True)

        if response.status_code >= 400:
            self.logger.info(u"%s http_get status code=%i" 
                % (self.provider_name, response.status_code))
            #raise provider.ProviderServerError("doi resolve")
        else:
            try:  
                # url the doi resolved to     
                redirected_url = response.url
                # remove session stuff at the end
                url_to_store = redirected_url.split(";jsessionid")[0]
                new_aliases += [("url", url_to_store)]
            except (TypeError, AttributeError):
                pass

        return new_aliases

