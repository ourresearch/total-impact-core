import time, re, urllib
from provider import Provider
from provider import ProviderError, ProviderTimeout, ProviderServerError
from provider import ProviderClientError, ProviderHttpError, ProviderContentMalformedError
from totalimpact.models import Aliases, Biblio
from xml.dom import minidom 
from xml.parsers.expat import ExpatError

import requests
import simplejson

import logging
logger = logging.getLogger('providers.dryad')

class Dryad(Provider):  

    metric_names = ["dryad:package_views", "dryad:total_downloads", "dryad:most_downloaded_file"]

    member_types = ["dryad_author"]
    metric_namespaces = ["doi"]
    alias_namespaces = ["doi"]
    biblio_namespaces = ["doi"]

    provides_members = False
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True

    example_id = ("doi", "10.5061/dryad.7898")


    # For Dryad the template is the same for all metrics
    # This template takes a doi
    provenance_url_template = "http://dx.doi.org/%s"

    member_items_url_template = "http://datadryad.org/solr/search/select/?q=dc.contributor.author%%3A%%22%s%%22&fl=dc.identifier"
    aliases_url_template = "http://datadryad.org/solr/search/select/?q=dc.identifier:%s&fl=dc.identifier.uri,dc.title"
    biblio_url_template = "http://datadryad.org/solr/search/select/?q=dc.identifier:%s&fl=dc.date.accessioned.year,dc.identifier.uri,dc.title_ac,dc.contributor.author_ac"
    metrics_url_template = "http://dx.doi.org/%s"

    def __init__(self):
        super(Dryad, self).__init__()
        
        self.dryad_doi_rx = re.compile(r"(10\.5061/.*)")
        self.member_items_rx = re.compile(r"(10\.5061/.*)</span")

        self.DRYAD_VIEWS_PACKAGE_PATTERN = re.compile("(?P<views>\d+)\W*views<span", re.DOTALL)
        self.DRYAD_DOWNLOADS_PATTERN = re.compile("(?P<downloads>\d+)\W*downloads</span", re.DOTALL)

    def _is_dryad_doi(self, doi):
        response = self.dryad_doi_rx.search(doi)
        return response is not None

    def _is_relevant_id(self, alias):
        return self._is_dryad_doi(alias[1])
    



    def member_items(self, 
            query_string, 
            query_type, 
            provider_url_template=None):
        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        enc = urllib.quote(query_string)

        url = provider_url_template % enc
        logger.debug("attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url)

        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)

        # did we get a page back that seems mostly valid?
        if ("response" not in response.text):
            raise ProviderContentMalformedError("Content does not contain expected text")

        identifiers = self._get_named_arr_str_from_xml(response.text, "dc.identifier", is_expected=False)

        return [("doi", hit.replace("doi:", "")) for hit in list(set(identifiers))]

    
    def aliases(self, 
            aliases, 
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.aliases_url_template

        # Get a list of the new aliases that can be discovered from the data
        # source.
        id_list = [alias[1] for alias in aliases if self._is_dryad_doi(alias[1])]

        if len(id_list) == 0:
            logger.info("warning, no DOI aliases found in the Dryad domain for this item")

        new_aliases = []
        for doi_id in id_list:
            logger.debug("processing alias %s" % doi_id)
            new_aliases += self._get_aliases_for_id(doi_id, provider_url_template)
        
        return new_aliases

    def _get_aliases_for_id(self, id, provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.aliases_url_template

        url = provider_url_template % id

        logger.debug("attempting to retrieve aliases from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url) 
        
        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)

        # did we get a page back that seems mostly valid?
        if ("response" not in response.text):
            raise ProviderContentMalformedError("Content does not contain expected text")
        
        # extract the aliases
        new_aliases = self._extract_aliases(response.text)
        if new_aliases is not None:
            logger.debug("Found aliases: " + str(new_aliases))
            return new_aliases
        return []


    def _extract_aliases(self, xml):
        identifiers = []
        url_identifiers = self._get_named_arr_str_from_xml(xml, u'dc.identifier.uri')
        identifiers += [("url", url) for url in url_identifiers]

        title_identifiers = self._get_named_arr_str_from_xml(xml, u'dc.title')
        identifiers += [("title", title) for title in title_identifiers]

        return identifiers

    def _get_dryad_doi(self, aliases):
        for doi in [res for (ns,res) in aliases if ns == 'doi']:
            if self._is_dryad_doi(doi):
                return doi
        return None

    def provenance_url(self, metric_name, aliases):
        # Dryad returns the same provenance url for all metrics
        # so ignoring the metric name
        dryad_doi = self._get_dryad_doi(aliases)
        if dryad_doi:
            provenance_url = self.provenance_url_template % dryad_doi
        else:
            provenance_url = None
            
        return provenance_url

    def metrics(self, 
            aliases,
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        id = self._get_dryad_doi(aliases)
        if id is not None:
            return self._get_metrics_for_id(id, provider_url_template)
        else:
            return None

    def _get_metrics_for_id(self, id, provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        url = provider_url_template % id

        logger.debug("attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url)

        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # did we get a page back that seems mostly valid?
        if ("Dryad" not in response.text):
            raise ProviderContentMalformedError("Content does not contain expected text")

        # extract the aliases
        return self._extract_stats(response.text)


    def _extract_stats(self, content):
        view_matches_package = self.DRYAD_VIEWS_PACKAGE_PATTERN.search(content)
        try:
            view_package = view_matches_package.group("views")
        except ValueError:
            raise ProviderContentMalformedError("Content does not contain expected text")
        
        download_matches = self.DRYAD_DOWNLOADS_PATTERN.finditer(content)
        try:
            downloads = [int(download_match.group("downloads")) for download_match in download_matches]
            total_downloads = sum(downloads)
            max_downloads = max(downloads)
        except ValueError:
            raise ProviderClientError(content)            

        return {
            "dryad:package_views": int(view_package),
            "dryad:total_downloads": int(total_downloads),
            "dryad:most_downloaded_file": int(max_downloads)
        }

    def biblio(self, 
            aliases,
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.biblio_url_template

        id = self._get_dryad_doi(aliases)
        # Only lookup biblio for items with dryad doi's
        if id:
            return self._get_biblio_for_id(id, provider_url_template)
        else:
            logger.info("Not checking biblio as no dryad doi")
            return None

    def _get_biblio_for_id(self, id, provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.biblio_url_template

        url = provider_url_template % id

        logger.debug("attempting to retrieve biblio from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url)
        
        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # extract the aliases
        return self._extract_biblio(response.text)

    def _extract_biblio(self, xml):
        biblio_dict = {}

        try:
            title = self._get_named_arr_str_from_xml(xml, 'dc.title_ac')
            biblio_dict["title"] = title[0]
        except AttributeError:
            raise ProviderContentMalformedError("Content does not contain expected text")

        try:
            year = self._get_named_arr_int_from_xml(xml, 'dc.date.accessioned.year')
            biblio_dict["year"] = year[0]
        except AttributeError:
            raise ProviderContentMalformedError("Content does not contain expected text")

        return biblio_dict

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

