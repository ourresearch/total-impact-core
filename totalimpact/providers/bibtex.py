from StringIO import StringIO
import json, re

from pybtex.database.input import bibtex
from pybtex.errors import enable_strict_mode, format_error
from pybtex.scanner import PybtexSyntaxError, PybtexError

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError
from totalimpact import unicode_helpers 
from totalimpact.providers import bibtex_lookup

import logging
logger = logging.getLogger('ti.providers.bibtex')



def build_bibtex_to_unicode(unicode_to_bibtex):
    bibtex_to_unicode = {}
    for unicode_value in unicode_to_bibtex:
        bibtex = unicode_to_bibtex[unicode_value]
        bibtex = unicode(bibtex, "utf-8")
        bibtex = bibtex.strip()
        bibtex = bibtex.replace("\\", "")
        bibtex = bibtex.replace("{", "")
        bibtex = bibtex.replace("}", "")
        bibtex = "{"+bibtex+"}"
        bibtex_to_unicode[bibtex] = unicode_value
    return bibtex_to_unicode


class Bibtex(Provider):  

    example_id = None

    url = ""
    descr = ""

    def __init__(self):
        super(Bibtex, self).__init__()
        enable_strict_mode(True) #throw errors
        self.bibtex_to_unicode = build_bibtex_to_unicode(bibtex_lookup.unicode_to_latex)

    def _to_unicode(self, text):
        text = unicode_helpers.to_unicode_or_bust(text)
        if "{" in text:
            text = text.replace("\\", "")
            for i, j in self.bibtex_to_unicode.iteritems():
                text = text.replace(i, j)
        return text

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
                logger.info(u"%20s NO DOI because no entries attribute in %s" % (self.provider_name, biblio))
                continue

            try:
                parsed["journal"] = self._to_unicode(biblio.entries[mykey].fields["journal"])
            except KeyError:
                parsed["journal"] = ""


            try:
                lnames = [person.get_part_as_text("last") for person in biblio.entries[mykey].persons["author"]]
                parsed["first_author"] = self._to_unicode(lnames[0])
            except (KeyError, AttributeError):
                try:
                    parsed["first_author"] = self._to_unicode(biblio.entries[mykey].fields["author"][0].split(",")[0])
                except (KeyError, AttributeError):
                    parsed["first_author"] = ""

            try:
                lnames = [person.get_part_as_text("last") for person in biblio.entries[mykey].persons["author"]]
                parsed["authors"] = self._to_unicode(", ".join(lnames))
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
                year_string = biblio.entries[mykey].fields["year"].replace("{}", "")
                parsed["year"] = re.sub("\D", "", year_string)
            except KeyError:
                parsed["year"]  = ""

            try:
                parsed["title"] = self._to_unicode(biblio.entries[mykey].fields["title"])
            except KeyError:
                parsed["title"]  = ""

            #parsed["key"] = mykey

            ret.append(parsed)

        return ret



    def member_items(self, bibtex_contents, cache_enabled=True):
        logger.debug(u"%20s getting member_items for bibtex" % (self.provider_name))

        parsed_bibtex = self.parse(bibtex_contents)

        aliases = []
        for entry in parsed_bibtex:
            if ("journal" in entry) and "arXiv preprint" in entry["journal"]:
                arxiv_id = entry["journal"].replace("arXiv preprint", "")
                arxiv_id = arxiv_id.replace("arXiv:", "").strip()
                aliases += [("arxiv", arxiv_id)]
            else:                
                aliases += [("biblio", entry)]

        return(aliases)
