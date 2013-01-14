from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError

from pybtex.database.input import bibtex
from pybtex.errors import enable_strict_mode, format_error
from pybtex.scanner import PybtexSyntaxError, PybtexError
from StringIO import StringIO
import json
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

        entry_strings = []
        for entry in biblio_list:

            if (entry["journal"] == ""):
                # need to have journal or can't look up with current api call
                logger.info("%20s NO DOI because no journal in %s" % (
                    self.provider_name, entry))
                continue

            entry_str =  ("|%s|%s|%s|%s|%s|%s||%s|" % (
                entry["journal"],
                entry["first_author"],
                entry["volume"],
                entry["number"],
                entry["first_page"],
                entry["year"],
                entry["key"]
                ))
            entry_strings.append(entry_str)

        if not entry_strings:
            return []

        text_str = "%0A".join(entry_strings)

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
                    logger.debug("%20s NO DOI from %s, %s" %(self.provider_name, entry, key))
                except KeyError:
                    logger.debug("%20s NO DOI from %s, %s" %(self.provider_name, "", key))                    

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
                parsed["journal"] = ""


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

            parsed["key"] = mykey

            ret.append(parsed)

        return ret





    def member_items(self, parsed_bibtex_json, cache_enabled=True):
        logger.debug("%20s getting member_items for bibtex" % (self.provider_name))
        parsed_bibtex = json.loads(parsed_bibtex_json)

        dois = self._lookup_dois_from_biblio(parsed_bibtex, cache_enabled)

        logger.debug("%20s dois: %s" % (self.provider_name, ", ".join(dois)))
        aliases = []
        for doi in dois:
            if doi and ("10." in doi):
                aliases += [("doi", doi)]

        return(aliases)
