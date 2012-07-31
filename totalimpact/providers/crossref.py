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

        (doc, lookup_function) = provider._get_doc_from_xml(page)
        try:
            contributors = doc.getElementsByTagName("contributors")[0]
            surname_list = []
            for person in contributors.getElementsByTagName("person_name"):
                if (person.getAttribute("contributor_role") == u"author"):
                    surname_list += [person.getElementsByTagName("surname")[0].firstChild.data]
        except IndexError:
            surnames = []
        authors = ", ".join(surname_list)
        if authors:
            biblio_dict["authors"] = authors

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"url": ["doi_record", "journal_article", "doi_data", "resource"], 
                            "title" : ["doi_record", "title"]}

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)

        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list




    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        logger.debug("%20s getting member_items for %s" % (self.provider_name, query_string))

        dois = []
        lines = query_string.split("\n")
        for line in lines:
            (first_author, title) = line.split("|")
            data = searchdoi(title, first_author)
            print data

            text_str = """<?xml version = "1.0" encoding="UTF-8"?>
                    <query_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns="http://www.crossref.org/qschema/2.0"
                      xsi:schemaLocation="http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd">
                    <head>
                       <email_address>totalimpactdev@gmail.com</email_address>
                       <doi_batch_id>test</doi_batch_id>
                    </head>
                    <body>
                      <query enable-multiple-hits="true"
                                list-components="false"
                                expanded-results="false" key="key">
                        <article_title match="fuzzy">Sharing Detailed Research Data Is Associated</article_title>
                        <author search-all-authors="false">Piwowar</author>
                        <component_number></component_number>
                        <edition_number></edition_number>
                        <institution_name></institution_name>
                        <volume></volume>
                        <issue></issue>
                        <year></year>
                        <first_page></first_page>
                        <journal_title></journal_title>
                        <proceedings_title></proceedings_title>
                        <series_title></series_title>
                        <volume_title></volume_title>
                        <unstructured_citation></unstructured_citation>
                      </query>
                    </body>
                    </query_batch>""" 

            #url = "http://doi.crossref.org/servlet/query?pid=totalimpactdev@gmail.com&qdata=%s" % text_str


            #print url

            #response = self.http_get(url, cache_enabled=cache_enabled)
            #print response.text


            dois += [data]

        aliases = []
        for doi in dois:
            if doi and ("10." in doi):
                aliases += [("doi", doi)]

        print aliases
        return(aliases)
