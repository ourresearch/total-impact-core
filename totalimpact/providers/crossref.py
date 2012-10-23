from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import BeautifulSoup

import logging
logger = logging.getLogger('ti.providers.crossref')

#!/usr/bin/env python

import httplib, urllib, re

# from http://tex.stackexchange.com/questions/6810/automatically-adding-doi-fields-to-a-hand-made-bibliography
# Search for the DOI given a title; e.g.  "computation in Noisy Radio Networks"
def searchdoi(title, author):
  params = urllib.urlencode({"titlesearch":"titlesearch", "auth2" : author, "atitle2" : title, "multi_hit" : "on", "article_title_search" : "Search", "queryType" : "author-title"})
  headers = {"User-Agent": "Mozilla/5.0" , "Accept": "text/html", "Content-Type" : "application/x-www-form-urlencoded", "Host" : "www.crossref.org"}
  conn = httplib.HTTPConnection("www.crossref.org:80")
  conn.request("POST", "/guestquery/", params, headers)
  response = conn.getresponse()
  #print response.status, response.reason
  data = response.read()
  conn.close()
  result = re.findall(r"doi:(10.\d+.[0-9a-zA-Z_/\.\-]+)" , data, re.DOTALL)
  if (len(result) > 0):
    doi = result[0]
  else:
      print("Bad response from server<br><br>") 
      doi = [] 
  return doi

class Crossref(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")
    url = "http://www.crossref.org/"
    descr = "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."
    biblio_url_template = None  #set in init
    aliases_url_template = "http://dx.doi.org/%s"

    def __init__(self):
        super(Crossref, self).__init__()
        common_url_template = "http://doi.crossref.org/servlet/query?pid=" + self.tool_email + "&qdata=%s&format=unixref"
        self.biblio_url_template = common_url_template


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['doi_record', 'title'],
            'year' : ['doi_record', 'year'],
            'journal_abbrev' : ['doi_record', 'abbrev_title'],
            'journal_full' : ['doi_record', 'full_title'],
        }
        biblio_dict = provider._extract_from_xml(page, dict_of_keylists)
        if not biblio_dict:
          return {}

        try:
            if "journal_abbrev" in biblio_dict:
                biblio_dict["journal"] = biblio_dict["journal_abbrev"]
                del biblio_dict["journal_abbrev"]
                del biblio_dict["journal_full"]
            elif "journal_full" in biblio_dict:
                biblio_dict["journal"] = biblio_dict["journal_full"]
                del biblio_dict["journal_full"]
        except (KeyError, TypeError):
            pass

        (doc, lookup_function) = provider._get_doc_from_xml(page)
        surname_list = []
        if doc:
            try:
                contributors = doc.getElementsByTagName("contributors")[0]
                for person in contributors.getElementsByTagName("person_name"):
                    if (person.getAttribute("contributor_role") == u"author"):
                        surname_list += [person.getElementsByTagName("surname")[0].firstChild.data]
            except IndexError:
                surname_list = []
        authors = ", ".join(surname_list)
        if authors:
            biblio_dict["authors"] = authors

        return biblio_dict    
       
    def _extract_aliases_old(self, page, id=None):
        dict_of_keylists = {"url": ["doi_record", "doi_data", "resource"]}

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)

        # add biblio to aliases
        biblio_dict = self._extract_biblio(page, id)
        if biblio_dict:
            aliases_dict["biblio"] = biblio_dict

        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list

    @property
    def provides_aliases(self):
         return True

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
        new_aliases = [("url", url)] # adds http://dx.doi.org/ url

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

