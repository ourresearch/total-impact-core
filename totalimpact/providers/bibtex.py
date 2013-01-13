from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError

from pybtex.database.input import bibtex
from pybtex.errors import enable_strict_mode, format_error
from pybtex.scanner import PybtexSyntaxError, PybtexError
from StringIO import StringIO
from itertools import chain

import logging
logger = logging.getLogger('ti.providers.bibtex')

class Bibtex(Provider):  

    example_id = ("bibtex", "egonw,cdk")

    url = ""
    descr = ""
    member_items_url_template = "https://api.github.com/users/%s/repos"

    def __init__(self):
        super(Bibtex, self).__init__()
        enable_strict_mode(True) #throw errors


    def _lookup_dois_from_biblio(self, biblio_list, cache_enabled):
        if not biblio_list:
            return []

        arg_dict = {}
        for biblio in biblio_list:
            #print "** parsing", biblio.entries[mykey]
            try:
                mykey = biblio.entries.keys()[0]
            except AttributeError:
                # doesn't seem to be a valid biblio object, so skip to the next one
                logger.info("%20s NO DOI because no entries attribute in %s" % (self.provider_name, biblio))                
                continue

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
            raise ProviderTimeout("CrossRef timeout")

        if response.status_code != 200:
            raise ProviderServerError("CrossRef status code was not 200")

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

    def _parse_bibtex_entries(self, entries):
        biblio_list = []
        for entry in entries:
            stream = StringIO(entry)
            parser = bibtex.Parser()
            try:
                biblio = parser.parse_stream(stream)
                biblio_list += [biblio]
            except (PybtexSyntaxError, PybtexError), error:
                logger.error(format_error(error, prefix='BIBTEX_ERROR: '))
                logger.error("BIBTEX_ERROR error input: '{entry}'".format(
                    entry=entry))
                #raise ProviderContentMalformedError(error.message)
        return biblio_list

    def paginate(self, bibtex_contents):
        logger.debug("%20s paginate in member_items" % (self.provider_name))

        cleaned_string = bibtex_contents.replace("\&", "").replace("%", "").strip()
        entries = ["@"+entry for entry in cleaned_string.split("@") if entry]

        items_per_page = 5
        layout = divmod(len(entries), items_per_page)
        last_page = min(1+layout[0], 50)  # 5 items/page * 50 pages = 250 items max  

        biblio_pages = []
        for i in xrange(0, last_page):
            last_item = min(i*items_per_page+items_per_page, len(entries))
            logger.debug("%20s parsing bibtex entries %i-%i of %i" % (self.provider_name, 1+i*items_per_page, last_item, len(entries)))
            biblio = self._parse_bibtex_entries(entries[0+i*items_per_page : last_item])
            if biblio:
                biblio_pages += [biblio]
        response_dict = {"pages":biblio_pages, "number_entries":len(entries)}
        return response_dict


    def parse(self, bibtex_contents):

        ret = []
        cleaned_string = bibtex_contents.replace("\&", "").replace("%", "").strip()
        entries = ["@"+entry for entry in cleaned_string.split("@") if entry]
        biblio_list = self._parse_bibtex_entries(entries)

        for biblio in biblio_list:
            parsed = {}
            try:
                mykey = biblio.entries.keys()[0]
            except AttributeError:
                # doesn't seem to be a valid biblio object, so skip to the next one
                logger.info("%20s NO DOI because no entries attribute in %s" % (self.provider_name, biblio))
                continue

            try:
                parsed["journal"] = biblio.entries[mykey].fields["journal"]
            except KeyError:
                # need to have journal or can't look up with current api call
                logger.info("%20s NO DOI because no journal in %s" % (self.provider_name, biblio.entries[mykey]))
                continue

            try:
                parsed["first_author"] = biblio.entries[mykey].fields["author"].split(",")[0]
            except (KeyError, AttributeError):
                parsed["first_author"] = biblio.entries[mykey].fields["author"][0].split(",")[0]

            try:
                parsed["number"] = biblio.entries[mykey].fields["number"]
            except KeyError:
                parsed["number"] = ""

            try:
                parsed["volume"] = biblio.entries[mykey].fields["volume"]
            except KeyError:
                parsed["volume"] = ""

            try:
                pages = biblio.entries[mykey].fields["pages"]
                parsed["first_page"] = pages.split("--")[0]
            except KeyError:
                parsed["first_page"] = ""

            try:
                parsed["year"] = biblio.entries[mykey].fields["year"]
            except KeyError:
                parsed["year"]  = ""

            ret.append(parsed)

        return ret





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
