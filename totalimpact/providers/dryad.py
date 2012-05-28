from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from xml.dom import minidom 
from xml.parsers.expat import ExpatError
import re

import logging
logger = logging.getLogger('providers.dryad')

class Dryad(Provider):  

    example_id = ("doi", "10.5061/dryad.7898")

    descr = "An international repository of data underlying peer-reviewed articles in the basic and applied biology."
    url = "http://www.datadryad.org"
    provenance_url_template = "http://dx.doi.org/%s"
    member_items_url_template = "http://datadryad.org/solr/search/select/?q=dc.contributor.author%%3A%%22%s%%22&fl=dc.identifier"
    aliases_url_template = "http://datadryad.org/solr/search/select/?q=dc.identifier:%s&fl=dc.identifier.uri,dc.title"
    biblio_url_template = "http://datadryad.org/solr/search/select/?q=dc.identifier:%s&fl=dc.date.accessioned.year,dc.identifier.uri,dc.title_ac,dc.contributor.author_ac"
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
        "most_downloaded_file":{
            "display_name": "most downloaded file",
            "provider": "Dryad",
            "provider_url": "http:\/\/www.datadryad.org\/",
            "description": "Dryad most downloaded file: number of downloads of the most commonly downloaded data package component",
            "icon": "http:\/\/datadryad.org\/favicon.ico",
        }
    }
        
    DRYAD_DOI_PATTERN = re.compile(r"(10\.5061/.*)")
    DRYAD_VIEWS_PACKAGE_PATTERN = re.compile("(?P<views>\d+)\W*views<span", re.DOTALL)
    DRYAD_DOWNLOADS_PATTERN = re.compile("(?P<downloads>\d+)\W*downloads</span", re.DOTALL)

    def __init__(self):
        super(Dryad, self).__init__()
        
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

    def _extract_members(self, page, query_string=None):
        if '<result name="response"' not in page:
            raise ProviderContentMalformedError("Content does not contain expected text")

        identifiers = self._get_named_arr_str_from_xml(page, "dc.identifier", is_expected=False)

        members = [("doi", hit.replace("doi:", "")) for hit in list(set(identifiers))]

        return(members)


    def _extract_aliases(self, xml, id=None):
        aliases = []
        url_identifiers = self._get_named_arr_str_from_xml(xml, u'dc.identifier.uri')
        aliases += [("url", url) for url in url_identifiers if url]

        title_identifiers = self._get_named_arr_str_from_xml(xml, u'dc.title')
        aliases += [("title", title) for title in title_identifiers if title]

        return aliases


    def _extract_biblio(self, xml, id=None):
        biblio_dict = {}

        biblio_dict["repository"] = "Dryad Digital Repository"

        try:
            title = self._get_named_arr_str_from_xml(xml, 'dc.title_ac')
            if title:
                biblio_dict["title"] = title[0]
        except AttributeError:
            raise ProviderContentMalformedError("Content does not contain expected text")

        try:
            year = self._get_named_arr_int_from_xml(xml, 'dc.date.accessioned.year')
            if year:
                biblio_dict["year"] = year[0]
        except AttributeError:
            raise ProviderContentMalformedError("Content does not contain expected text")

        try:
            arrs = self._get_named_arrs_from_xml(xml, 'dc.contributor.author_ac')

            authors = []
            for arr in arrs:
                node = arr.getElementsByTagName('str')
                for author in node:
                    full_name = author.firstChild.nodeValue
                    last_name = full_name.split(",")[0]
                    authors.append(last_name)

            if authors:
                biblio_dict["authors"] = (", ").join(authors)
        except AttributeError:
            raise ProviderContentMalformedError("Content does not contain expected text")

        return biblio_dict


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        view_matches_package = self.DRYAD_VIEWS_PACKAGE_PATTERN.search(page)
        try:
            view_package = view_matches_package.group("views")
        except (ValueError, AttributeError):
            raise ProviderContentMalformedError("Content does not contain expected text")
        
        download_matches = self.DRYAD_DOWNLOADS_PATTERN.finditer(page)
        try:
            downloads = [int(download_match.group("downloads")) for download_match in download_matches]
            total_downloads = sum(downloads)
            max_downloads = max(downloads)
        except (ValueError, AttributeError):
            raise ProviderContentMalformedError("Content does not contain expected text")            

        metrics_dict = {
            "dryad:package_views": int(view_package),
            "dryad:total_downloads": int(total_downloads),
            "dryad:most_downloaded_file": int(max_downloads)
        }

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
            doc = minidom.parseString(xml)
        except ExpatError, e:
            raise ProviderContentMalformedError("Content parse provider supplied XML document")
        arrs = doc.getElementsByTagName('arr')
        matching_arrs = [elem for elem in arrs if elem.attributes['name'].value == name]
        if (is_expected and (len(matching_arrs) == 0)):
            raise ProviderContentMalformedError("Did not find expected number of matching arr blocks")

        return matching_arrs

