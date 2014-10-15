from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError
from totalimpact.unicode_helpers import remove_nonprinting_characters
import itertools
import httplib, urllib, re

import logging
logger = logging.getLogger('ti.providers.crossref')

#!/usr/bin/env python

def clean_doi(input_doi):
    input_doi = remove_nonprinting_characters(input_doi)
    try:
        input_doi = input_doi.lower()
        if input_doi.startswith("http"):
            match = re.match("^https*://(dx\.)*doi.org/(10\..+)", input_doi)
            doi = match.group(2)
        elif "doi.org" in input_doi:
            match = re.match("^(dx\.)*doi.org/(10\..+)", input_doi)
            doi = match.group(2)
        elif input_doi.startswith("doi:"):
            match = re.match("^doi:(10\..+)", input_doi)
            doi = match.group(1)
        elif input_doi.startswith("10."):
            doi = input_doi
        elif "10." in input_doi:
            match = re.match(".*(10\.\d+.+)", input_doi, re.DOTALL)
            doi = match.group(1)
        else:
            doi = None
            try:
                logger.debug(u"MALFORMED DOI {input_doi}".format(
                    input_doi=input_doi))
            except:
                logger.debug(u"MALFORMED DOI, can't print doi")


    except AttributeError:
        doi = None

    return doi


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

    @property
    def provides_biblio(self):
         return True

    # overriding default because overriding member_items method
    @property
    def provides_members(self):
        return True

    # default method; providers can override
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug(u"%s /biblio_print getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = provider_url_template % id

        self.logger.debug(u"%s /biblio_print _lookup_biblio_from_doi for %s" % (self.provider_name, id))
        biblio_dict = self._lookup_biblio_from_doi(id, url, cache_enabled)

        self.logger.debug(u"%s /biblio_print _lookup_issn_from_doi for %s" % (self.provider_name, id))
        biblio_dict.update(self._lookup_issn_from_doi(id, url, cache_enabled))

        self.logger.debug(u"%s /biblio_print free_fulltext_fragments for %s" % (self.provider_name, id))
        
        free_fulltext_fragments = ["/npre.", "/peerj.preprints"]
        if any(doi_fragment in id for doi_fragment in free_fulltext_fragments):
            biblio_dict["free_fulltext_url"] = url
        elif ("issn" in biblio_dict) and provider.is_issn_in_doaj(biblio_dict["issn"]):
            biblio_dict["free_fulltext_url"] = url

        return biblio_dict


    def _lookup_issn_from_doi(self, id, url, cache_enabled):
        # try to get a response from the data provider      
        response = self.http_get(url, 
            cache_enabled=cache_enabled, 
            allow_redirects=True,
            headers={"Accept": "application/json", "User-Agent": "impactstory.org"})

        if response.status_code != 200:
            self.logger.info(u"%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404: #not found
                return {}
            elif response.status_code == 403: #forbidden
                return {}
            elif (response.status_code == 406) or (response.status_code == 500): #this call isn't supported for datacite dois
                return {}
            elif ((response.status_code >= 300) and (response.status_code < 400)): #redirect
                return {}
            else:
                self._get_error(response.status_code, response)

        # extract the aliases
        try:
            biblio_dict = self._extract_biblio_issn(response.text, id)
        except (AttributeError, TypeError):
            biblio_dict = {}

        return biblio_dict


    def _extract_biblio_issn(self, page, id=None):
        dict_of_keylists = {
            'issn' : ['ISSN']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)
        if not biblio_dict:
          return {}

        if "issn" in biblio_dict:
            biblio_dict["issn"] = biblio_dict["issn"][0].replace("-", "")

        return biblio_dict  


    def _lookup_biblio_from_doi(self, id, url, cache_enabled):
        # try to get a response from the data provider        
        response = self.http_get(url, 
            cache_enabled=cache_enabled, 
            allow_redirects=True,
            headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": "impactstory.org"})

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
                biblio_dict["authors"] = u", ".join(surname_list)
                del biblio_dict["authors_literal"]
        except (IndexError, KeyError):
            try:
                literal_list = [author["literal"] for author in biblio_dict["authors_literal"]]
                if literal_list:
                    biblio_dict["authors_literal"] = u"; ".join(literal_list)
            except (IndexError, KeyError):
                pass

        try:
            if "year" in biblio_dict:
                if "raw" in biblio_dict["year"]:
                    biblio_dict["year"] = str(biblio_dict["year"]["raw"])
                elif "date-parts" in biblio_dict["year"]:
                    biblio_dict["year"] = str(biblio_dict["year"]["date-parts"][0][0])
                biblio_dict["year"] = re.sub("\D", "", biblio_dict["year"])
                if not biblio_dict["year"]:
                    del biblio_dict["year"]

        except IndexError:
            logger.info(u"/biblio_print could not parse year {biblio_dict}".format(
                biblio_dict=biblio_dict))
            del biblio_dict["year"]

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

        doi = None
        new_aliases = []

        if "doi" in aliases_dict:
            doi = aliases_dict["doi"][0]
        else:
            if "url" in aliases_dict:
                for url in aliases_dict["url"]:
                    if url.startswith("http://dx.doi.org/"):
                        doi = url.replace("http://dx.doi.org/", "")
                        new_aliases += [("doi", doi)]
                    elif url.startswith("http://doi.org/"):
                        doi = url.replace("http://doi.org/", "")
                        new_aliases += [("doi", doi)]

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
                logger.info(u"%20s /biblio_print NO DOI because no journal in %s" % (
                    self.provider_name, biblio))
                return []
            query_string =  (u"|%s|%s|%s|%s|%s|%s||%s|" % (
                biblio.get("journal", ""),
                biblio.get("first_author", biblio.get("authors", "").split(",")[0].strip()),
                biblio.get("volume", ""),
                biblio.get("number", ""),
                biblio.get("first_page", ""),
                biblio.get("year", ""),
                "ImpactStory"
                ))
        except KeyError:
            logger.info(u"%20s /biblio_print NO DOI because missing needed attribute in %s" % (
                self.provider_name, biblio))
            return []


        # for more info on crossref spec, see
        # http://ftp.crossref.org/02publishers/25query_spec.html
        url = "http://doi.crossref.org/servlet/query?pid=totalimpactdev@gmail.com&qdata=%s" % query_string

        try:
            logger.debug(u"%20s /biblio_print calling crossref at %s" % (self.provider_name, url))
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
                    logger.debug(u"%20s /biblio_print NO DOI from %s, %s" %(self.provider_name, biblio, key))
                except KeyError:
                    logger.debug(u"%20s /biblio_print NO DOI from %s, %s" %(self.provider_name, "", key))                    

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


    # overriding because don't need to look up
    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_members:
            raise NotImplementedError()

        self.logger.debug(u"%s getting member_items for %s" % (self.provider_name, query_string))

        doi_string = query_string.strip(" ")
        if not doi_string:
            return []
        dois = [clean_doi(doi) for doi in doi_string.split("\n")]
        aliases_tuples = [("doi", doi) for doi in dois if doi]

        return(aliases_tuples)


