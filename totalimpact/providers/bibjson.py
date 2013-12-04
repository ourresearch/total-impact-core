from StringIO import StringIO
import json, re

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderTimeout, ProviderServerError
from totalimpact import unicode_helpers 

import logging
logger = logging.getLogger('ti.providers.bibjson')


class Bibjson(Provider):  

    example_id = None

    url = ""
    descr = ""

    def _to_unicode(self, text):
        text = unicode_helpers.to_unicode_or_bust(text)
        return text


    def parse(self, bibjson_list):
        ret = []
        for bibjson_entry in bibjson_list:
            full_entry = bibjson_entry
            try:
                full_entry["authors"] = self._to_unicode(re.sub(", \d+", "", full_entry["marker"]))
            except (KeyError, AttributeError):
                full_entry["authors"] = ""

            try:
                full_entry["first_author"] = self._to_unicode(full_entry["marker"].split(",")[0])
            except (KeyError, AttributeError):
                full_entry["first_author"] = ""

            try:
                pages = full_entry["pages"]
                full_entry["first_page"] = pages.split("--")[0]
            except KeyError:
                full_entry["first_page"] = ""

            try:
                full_entry["title"] = full_entry["booktitle"]
            except (KeyError, AttributeError):
                pass

            ret.append(full_entry)

        return ret



    def member_items(self, bibjson_contents, cache_enabled=True):
        logger.debug(u"%20s getting member_items for bibjson" % (self.provider_name))

        parsed_bibjson = self.parse(bibjson_contents)

        aliases = [("biblio", entry) for entry in parsed_bibjson]

        return(aliases)
