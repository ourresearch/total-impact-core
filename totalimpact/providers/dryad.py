from totalimpact.providers import provider
from totalimpact.providers import crossref
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderItemNotFoundError
from xml.dom import minidom 
from xml.parsers.expat import ExpatError
import re

import logging
logger = logging.getLogger('ti.providers.dryad')

class Dryad(Provider):  

    example_id = ("doi", "10.5061/dryad.7898")

    descr = "An international repository of data underlying peer-reviewed articles in the basic and applied biology."
    url = "http://www.datadryad.org"
    provenance_url_template = "http://dx.doi.org/%s"
    # No aliases_url_template because uses crossref
    # No biblio_url_template because uses crossref
    metrics_url_template = "http://dx.doi.org/%s"

    static_meta_dict = {
        "package_views": {
            "display_name": "package views",
            "provider": "Dryad",
            "provider_url": "http:\/\/www.datadryad.org\/",
            "description": "Dryad package views: number of views of the main package page",
            "icon": "http:\/\/datadryad.org\/favicon.ico",
        },
        "total_downloads": {
            "display_name": "total downloads",
            "provider": "Dryad",
            "provider_url": "http:\/\/www.datadryad.org\/",
            "description": "Dryad total downloads: combined number of downloads of the data package and data files",
            "icon": "http:\/\/datadryad.org\/favicon.ico",
        },
    }
        
    DRYAD_DOI_PATTERN = re.compile(r"(10\.5061/.*)")
    DRYAD_VIEWS_PACKAGE_PATTERN = re.compile("<th>Pageviews</th>\W*<td>(?P<views>\d+)</td>\W*</tr>", re.DOTALL)
    DRYAD_DOWNLOADS_PATTERN = re.compile("<tr>\W*<th>Downloaded</th>\W*<td>(?P<downloads>\d+) times</td>\W*</tr>", re.DOTALL)

    def __init__(self):
        super(Dryad, self).__init__()
        self.crossref = crossref.Crossref()
        
    def _is_dryad_doi(self, doi):
        response = self.DRYAD_DOI_PATTERN.search(doi)
        if response:
            return(True)
        else:
            return(False)

    def _get_dryad_doi(self, aliases):
        for doi in [nid for (namespace, nid) in aliases if namespace == 'doi']:
            if self._is_dryad_doi(doi):
                return doi
        return None

    def is_relevant_alias(self, alias):
        if not alias:
            return False
        (namespace, nid) = alias
        is_relevant = (namespace=="doi" and self._is_dryad_doi(nid))
        return is_relevant

    @property
    def provides_aliases(self):
         return True

    @property
    def provides_biblio(self):
         return True

    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):  
        logger.info(u"calling crossref to handle aliases")
        return self.crossref.aliases(aliases, provider_url_template, cache_enabled)          

    def biblio(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):  
        logger.info(u"calling crossref to handle aliases")
        biblio = self.crossref.biblio(aliases, provider_url_template, cache_enabled)          

        # try to parse out last names, for now using most basic approach
        if not biblio:
            return {}
        if "authors_literal" in biblio:
            lnames = [author.split(u",")[0] for author in biblio["authors_literal"].split(u";")]
            biblio["authors"] = u",".join(lnames)
            del biblio["authors_literal"]
        return biblio

    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 303:
                pass #this is ok
            elif status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if "Dryad" not in page:
            raise ProviderContentMalformedError

        metrics_dict = {}

        view_matches_package = self.DRYAD_VIEWS_PACKAGE_PATTERN.search(page)
        try:
            views = int(view_matches_package.group("views"))
            if views:
                metrics_dict["dryad:package_views"] = views
        except (ValueError, AttributeError):
            pass
        
        download_matches = self.DRYAD_DOWNLOADS_PATTERN.finditer(page)
        try:
            downloads = [int(download_match.group("downloads")) for download_match in download_matches]
            downloads_sum = sum(downloads)
            if downloads_sum:
                metrics_dict["dryad:total_downloads"] = downloads_sum
        except (ValueError, AttributeError):
            pass

        return metrics_dict


    def _get_named_arr_int_from_xml(self, xml, name, is_expected=True):
        """ Find the first node in the XML <arr> sections which are of node type <int>
            and return their text values. """
        identifiers = []
        arrs = self._get_named_arrs_from_xml(xml, name, is_expected)
        for arr in arrs:
            node = arr.getElementsByTagName('int')[0]
            identifiers.append(node.firstChild.nodeValue)
        return identifiers

    def _get_named_arr_str_from_xml(self, xml, name, is_expected=True):
        """ Find the first node in the XML <arr> sections which are of node type <str>
            and return their text values. """
        identifiers = []
        arrs = self._get_named_arrs_from_xml(xml, name, is_expected)

        for arr in arrs:
            node = arr.getElementsByTagName('str')[0]
            identifiers.append(node.firstChild.nodeValue)
        return identifiers

    def _get_named_arrs_from_xml(self, xml, name, is_expected=True):
        """ Find <arr> sections in the given xml document which have a
            match for the name attribute """
        try:
            doc = minidom.parseString(xml.encode('utf-8'))
        except ExpatError, e:
            raise ProviderContentMalformedError("Content parse provider supplied XML document")
        arrs = doc.getElementsByTagName('arr')
        matching_arrs = [elem for elem in arrs if elem.attributes['name'].value == name]
        if (is_expected and (len(matching_arrs) == 0)):
            raise ProviderContentMalformedError("Did not find expected number of matching arr blocks")

        return matching_arrs

