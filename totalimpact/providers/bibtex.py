from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout

import simplejson
import pybtex
from pybtex.database.input import bibtex
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
        stream = StringIO("\n".join(entries))
        parser = bibtex.Parser()
        try:
            biblio = parser.parse_stream(stream)
        except:
            raise ProviderContentMalformedError()
        return biblio

    def _lookup_dois_from_biblio(self, biblio, cache_enabled):
        if not biblio:
            return []

        arg_dict = {}
        for mykey in biblio.entries:
            #print "** parsing", biblio.entries[mykey]

            try:
                journal = biblio.entries[mykey].fields["journal"]
            except KeyError:
                # need to have journal or can't look up with current api call
                logger.info("%20s NO DOI because no journal in %s" % (self.provider_name, biblio.entries[mykey]))
                continue

            try:
                first_author = biblio.entries[mykey].fields["author"].split(",")[0]
            except (KeyError, AttributeError):
                first_author = biblio.entries[mykey].fields["author"][0].split(",")[0]

            try:
                number = biblio.entries[mykey].fields["number"]
            except KeyError:
                number = ""

            try:
                volume = biblio.entries[mykey].fields["volume"]
            except KeyError:
                volume = ""

            try:
                pages = biblio.entries[mykey].fields["pages"]
                first_page = pages.split("--")[0]
            except KeyError:
                first_page = ""

            try:
                year = biblio.entries[mykey].fields["year"]
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
                try:
                    logger.debug("%20s NO DOI from %s, %s" %(self.provider_name, arg_dict[key], key))
                except KeyError:
                    logger.debug("%20s NO DOI from %s, %s" %(self.provider_name, "", key))                    
                
                try:
                    logger.debug("%20s full bibtex for NO DOI is %s" %(self.provider_name, biblio.entries[key]))
                except KeyError:
                    pass

        non_empty_dois = [doi for doi in dois if doi]
        logger.debug("%20s found %i dois" % (self.provider_name, len(non_empty_dois)))

        return non_empty_dois


    def paginate(self, bibtex_contents):
        logger.debug("%20s paginate in member_items" % (self.provider_name))

        cleaned_string = bibtex_contents.replace("\&", "").replace("%", "").strip()
        entries = ["@"+entry for entry in cleaned_string.split("@") if entry]
        #print entries

        items_per_page = 5
        layout = divmod(len(entries), items_per_page)
        last_page = min(1+layout[0], 50)  # 5 items/page * 50 pages = 250 items max  

        biblio_pages = []
        for i in xrange(0, last_page):
            last_item = min(i*items_per_page+items_per_page, len(entries))
            logger.debug("%20s parsing bibtex entries %i-%i of %i" % (self.provider_name, 1+i*items_per_page, last_item, len(entries)))
            biblio_pages += [self._parse_bibtex_entries(entries[1+i*items_per_page : last_item])]
        response_dict = {"pages":biblio_pages, "number_entries":len(entries)}
        return response_dict


    def member_items(self, parsed_bibtex, cache_enabled=True):
        logger.debug("%20s getting member_items for bibtex" % (self.provider_name))

        if not parsed_bibtex:
            return []

        dois = self._lookup_dois_from_biblio(parsed_bibtex, cache_enabled)

        logger.debug("%20s dois: %s" % (self.provider_name, ", ".join(dois)))
        aliases = []
        for doi in dois:
            if doi and ("10." in doi):
                aliases += [("doi", doi)]

        return(aliases)
