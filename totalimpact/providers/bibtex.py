from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError
from totalimpact import utils 

from pybtex.database.input import bibtex
from pybtex.errors import enable_strict_mode, format_error
from pybtex.scanner import PybtexSyntaxError, PybtexError
from StringIO import StringIO
import json

import logging
logger = logging.getLogger('ti.providers.bibtex')

class Bibtex(Provider):  

    example_id = None

    url = ""
    descr = ""

    def __init__(self):
        super(Bibtex, self).__init__()
        enable_strict_mode(True) #throw errors

    def _parse_bibtex_entries(self, entries):
        biblio_list = []
        for entry in entries:
            stream = StringIO(entry)
            parser = bibtex.Parser()
            try:
                biblio = parser.parse_stream(stream)
                biblio_list += [biblio]
            except (PybtexSyntaxError, PybtexError), error:
                error = error
                logger.error(format_error(error, prefix='BIBTEX_ERROR: '))
                #logger.error("BIBTEX_ERROR error input: '{entry}'".format(
                #    entry=entry))
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


            lnames = [person.get_part_as_text("last") for person in biblio.entries[mykey].persons["author"]]
            try:
                parsed["first_author"] = lnames[0]
            except (KeyError, AttributeError):
                parsed["first_author"] = biblio.entries[mykey].fields["author"][0].split(",")[0]

            try:
                parsed["authors"] = ", ".join(lnames)
            except (KeyError, AttributeError):
                parsed["authors"] = ""

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

            try:
                parsed["title"] = biblio.entries[mykey].fields["title"]
            except KeyError:
                parsed["title"]  = ""

            #parsed["key"] = mykey

            ret.append(parsed)

        return ret



    def member_items(self, parsed_bibtex_json, cache_enabled=True):
        logger.debug("%20s getting member_items for bibtex" % (self.provider_name))

        parsed_bibtex = json.loads(parsed_bibtex_json)

        aliases = [("biblio", entry) for entry in parsed_bibtex]

        return(aliases)
