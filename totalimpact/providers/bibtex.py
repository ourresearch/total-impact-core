from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout

import simplejson
from zs.bibtex.parser import parse_string
from pyparsing import ParseException
from StringIO import StringIO
import re

import logging
logger = logging.getLogger('ti.providers.bibtex')

class Bibtex(Provider):  

    example_id = ("bibtex", "egonw,cdk")

    url = ""
    descr = ""
    member_items_url_template = "https://api.github.com/users/%s/repos"

    def __init__(self):
        super(Bibtex, self).__init__()


    def _parse_bibtex_entries(self, entries):
        biblio = {}        
        for entry in entries:
            try:
                entry_parsed = parse_string(entry)
                biblio.update(entry_parsed)
            except ParseException, e:  
                logger.error("%20s NOT ABLE TO PARSE %s" % (self.provider_name, e))
        return biblio

    def _lookup_dois_from_biblio(self, biblio, cache_enabled):
        if not biblio:
            return []

        arg_dict = {}
        for mykey in biblio:
            #print "** parsing", biblio[mykey]

            try:
                journal = biblio[mykey]["journal"]
            except KeyError:
                # need to have journal or can't look up with current api call
                logger.info("%20s NO DOI because no journal in %s" % (self.provider_name, biblio[mykey]))
                continue

            try:
                first_author = biblio[mykey]["author"].split(",")[0]
            except (KeyError, AttributeError):
                first_author = biblio[mykey]["author"][0].split(",")[0]

            try:
                number = biblio[mykey]["number"]
            except KeyError:
                number = ""

            try:
                volume = biblio[mykey]["volume"]
            except KeyError:
                volume = ""

            try:
                pages = biblio[mykey]["pages"]
                first_page = pages.split("--")[0]
            except KeyError:
                first_page = ""

            try:
                year = biblio[mykey]["year"]
            except KeyError:
                year = ""

            arg_dict[mykey] = ("|%s|%s|%s|%s|%s|%s||%s|" % (journal, first_author, volume, number, first_page, year, mykey))

        if not arg_dict:
            return []

        text_str = "%0A".join(arg_dict.values())
        # for more info on crossref spec, see
        # http://ftp.crossref.org/02publishers/25query_spec.html
        url = "http://doi.crossref.org/servlet/query?pid=totalimpactdev@gmail.com&qdata=%s" % text_str

        logger.debug("%20s calling crossref at %s" % (self.provider_name, url))
        # doi-lookup call to crossref can take a while, give it a long timeout

        try:
            response = self.http_get(url, timeout=30, cache_enabled=cache_enabled)
        except ProviderTimeout:
            return []

        response_lines = response.text.split("\n")
        #import pprint
        #pprint.pprint(biblio)

        split_lines = [line.split("|") for line in response_lines if line]
        line_keys = [line[-2].strip() for line in split_lines]
        dois = [line[-1].strip() for line in split_lines]

        for key, doi in zip(line_keys, dois):
            if not doi:
                logger.debug("%20s NO DOI from %s, %s" %(self.provider_name, arg_dict[key], key))
                logger.debug("%20s full bibtex for NO DOI is %s" %(self.provider_name, biblio[key]))

        non_empty_dois = [doi for doi in dois if doi]
        logger.debug("%20s found %i dois" % (self.provider_name, len(non_empty_dois)))

        return non_empty_dois


    def paginate(self, bibtex_contents):
        logger.debug("%20s paginate in member_items" % (self.provider_name))

        cleaned_string = bibtex_contents.replace("\&", "").replace("%", "")
        entries = ["@"+entry for entry in cleaned_string.split("@")]
        #print entries

        items_per_page = 5
        layout = divmod(len(entries), items_per_page)
        last_page = min(1+layout[0], 25)  # 20 items/page * 25 pages = 500 items max  

        biblio_pages = []
        for i in xrange(0, last_page):
            last_item = min(i*items_per_page+items_per_page, len(entries))
            logger.debug("%20s parsing bibtex entries %i-%i of %i" % (self.provider_name, 1+i*items_per_page, last_item, len(entries)))
            biblio_pages += [self._parse_bibtex_entries(entries[1+i*items_per_page : last_item])]
        return(biblio_pages)


    def member_items(self, parsed_bibtex, cache_enabled=True):
        logger.debug("%20s getting member_items for bibtex" % (self.provider_name))
        if not parsed_bibtex:
            return []

        #print parsed_bibtex
        try:
            parsed_bibtex.keys()
        except AttributeError:  
            raise provider.ProviderServerError("did not receive a dictionary in bibtex member_items")

        dois = self._lookup_dois_from_biblio(parsed_bibtex, cache_enabled)

        logger.debug("%20s dois: %s" % (self.provider_name, "\n".join(dois)))
        aliases = []
        for doi in dois:
            if doi and ("10." in doi):
                aliases += [("doi", doi)]

        return(aliases)
