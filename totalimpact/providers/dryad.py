import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Metrics, ProviderMetric, Aliases, Biblio
from bs4 import BeautifulSoup

import requests
import simplejson

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class DryadMetricSnapshot(ProviderMetric):
    def __init__(self, provider, id, value):
        meta = provider.config.metrics["static_meta"][id]
        super(DryadMetricSnapshot, self).__init__(id=id, value=value, meta=meta)

class Dryad(Provider):  

    def __init__(self, config, app_config=None):
        super(Dryad, self).__init__(config, app_config)
        self.state = DryadState(config)
        self.id = self.config.id
        
        self.dryad_doi_rx = re.compile(r"(10\.5061/.*)")
        self.member_items_rx = re.compile(r"(10\.5061/.*)</span")

        self.DRYAD_VIEWS_PACKAGE_PATTERN = re.compile("(?P<views>\d+) views</span>", re.DOTALL)
        self.DRYAD_VIEWS_FILE_PATTERN = re.compile("(?P<views>\d+) views\S", re.DOTALL)
        self.DRYAD_DOWNLOADS_PATTERN = re.compile("(?P<downloads>\d+) downloads", re.DOTALL)

    def _is_dryad_doi(self, doi):
        return self.dryad_doi_rx.search(doi) is not None

    def _is_relevant_id(self, alias):
        return self._is_dryad_doi(alias[1])

    def _get_named_arr_int_from_xml(self, xml, name, is_expected=True):
        arrs = self._get_named_arrs_from_xml(xml, name, is_expected)
        identifiers = [arr.int.text for arr in arrs]
        return identifiers

    def _get_named_arr_str_from_xml(self, xml, name, is_expected=True):
        arrs = self._get_named_arrs_from_xml(xml, name, is_expected)
        identifiers = [arr.str.text for arr in arrs]
        return identifiers

    def _get_named_arrs_from_xml(self, xml, name, is_expected=True):
#        soup = BeautifulSoup(xml, ["lxml", "xml"])
        soup = BeautifulSoup(xml)

        try:
            # use attrs approach here because "name" is an attribute name for find_all method itself
            arrs = soup.find_all("arr", attrs={'name':name}) 
        except AttributeError:
            raise ProviderClientError(soup.text)
        if (is_expected and (len(arrs) == 0)):
            raise ProviderClientError(soup.text) 
        return (arrs)


    def member_items(self, query_string, query_type):
        enc = urllib.quote(query_string)

        url = self.config.member_items["querytype"]["dryadAuthor"]['url'] % enc
        logger.debug(self.config.id + ": query type " + query_type)
        logger.debug(self.config.id + ": attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.member_items.get('timeout', None))

        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)

        # did we get a page back that seems mostly valid?
        if ("response" not in response.text):
            raise ProviderClientError(response)

        identifiers = self._get_named_arr_str_from_xml(response.text, "dc.identifier", is_expected=False)

        return [(Aliases.NS.DOI, hit.replace("doi:", "")) for hit in list(set(identifiers))]

    
    def aliases(self, item): 
        # get the alias object
        alias_object = item.aliases
        logger.info(self.config.id + ": aliases requested for tiid:" + alias_object.tiid)
        
        # Get a list of the new aliases that can be discovered from the data
        # source
        new_aliases = []
        for alias in alias_object.get_aliases_list(self.config.supported_namespaces):
            if not self._is_dryad_doi(alias[1]):
                continue
            logger.debug(self.config.id + ": processing aliases for tiid:" + alias_object.tiid)
            new_aliases += self._get_aliases(alias)
        
        # update the original alias object with new unique aliases
        alias_object.add_unique(new_aliases)
        
        # log our success
        logger.debug(self.config.id + ": discovered aliases for tiid " + alias_object.tiid + ": " + str(new_aliases))
        logger.info(self.config.id + ": aliases completed for tiid:" + alias_object.tiid)
        
        # no need to set the aliases on the item, as everything is by-reference
        return item
        

    def _get_aliases(self, alias):
        # FIXME: urlencoding?
        url = self.config.aliases['url'] % alias[1]
        logger.debug(self.config.id + ": attempting to retrieve aliases from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.aliases.get('timeout', None))
        
        # register the hit, mostly so that anyone copying this remembers to do it,
        # - we have overriden this in the DryadState object, so it doesn't do anything
        self.state.register_unthrottled_hit()
        
        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)

        # did we get a page back that seems mostly valid?
        if ("response" not in response.text):
            raise ProviderClientError(response)
        
        # extract the aliases
        new_aliases = self._extract_aliases(response.text)
        if new_aliases is not None:
            logger.debug(self.config.id + ": found aliases: " + str(new_aliases))
            return new_aliases
        return []


    def _extract_aliases(self, xml):
        identifiers = []
        url_identifiers = self._get_named_arr_str_from_xml(xml, u'dc.identifier.uri')
        identifiers += [(Aliases.NS.URL, url) for url in url_identifiers]

        title_identifiers = self._get_named_arr_str_from_xml(xml, u'dc.title')
        identifiers += [(Aliases.NS.TITLE, title) for title in title_identifiers]

        return identifiers

    def provides_metrics(self): 
        return True
    
    def get_show_details_url(self, doi):
        return "http://dx.doi.org/" + doi

    def _get_dryad_doi(self, item):
        item_dois = item.aliases.get_ids_by_namespace(Aliases.NS.DOI)
        item_dryad_dois = [doi for doi in item_dois if self._is_dryad_doi(doi)]
        if not item_dryad_dois:
            raise Exception
        id = item_dryad_dois[0]
        return(id)        

    def metrics(self, item):
        id = self._get_dryad_doi(item)
        
        url = self.config.metrics['url'] % urllib.quote(id)
        logger.debug(self.config.id + ": attempting to retrieve metrics from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.metrics.get('timeout', None))
        
        # register the hit, mostly so that anyone copying this remembers to do it,
        # - we have overriden this in the DryadState object, so it doesn't do anything
        self.state.register_unthrottled_hit()
        
        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # did we get a page back that seems mostly valid?
        if ("Dryad" not in response.text):
            raise ProviderClientError(response)

        # extract the aliases
        new_stats = self._extract_stats(response.text)
        metrics = Metrics()

        if new_stats is not None:
            for metric in new_stats:
                logger.debug(self.config.id + ": found metrics: " + str(metric))
                metrics.add_provider_metric(metric)
            return metrics
        return []


    def _extract_stats(self, content):
        view_matches_package = self.DRYAD_VIEWS_PACKAGE_PATTERN.finditer(content)
        view_matches_file = self.DRYAD_VIEWS_FILE_PATTERN.finditer(content)
        try:
            view_package = max([int(view_match.group("views")) for view_match in view_matches_package])
            file_total_views = sum([int(view_match.group("views")) for view_match in view_matches_file]) - view_package
        except ValueError:
            raise ProviderClientError(content)            
        
        download_matches = self.DRYAD_DOWNLOADS_PATTERN.finditer(content)
        try:
            downloads = [int(download_match.group("downloads")) for download_match in download_matches]
            total_downloads = sum(downloads)
            max_downloads = max(downloads)
        except ValueError:
            raise ProviderClientError(content)            

        snapshot_file_views = DryadMetricSnapshot(self, "Dryad:file_views", file_total_views)
        snapshot_view_package = DryadMetricSnapshot(self, "Dryad:package_views", view_package)
        snapshot_total_downloads = DryadMetricSnapshot(self, "Dryad:total_downloads", total_downloads)
        snapshot_most_downloaded_file = DryadMetricSnapshot(self, "Dryad:most_downloaded_file", max_downloads)

        return([snapshot_file_views, snapshot_view_package, snapshot_total_downloads, snapshot_most_downloaded_file])


    def provides_biblio(self): 
        return True

    def biblio(self, item): 
        id = self._get_dryad_doi(item)

        url = self.config.biblio['url'] % urllib.quote(item.id)

        print url

        logger.debug(self.config.id + ": attempting to retrieve biblio from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.biblio.get('timeout', None))
        
        # register the hit, mostly so that anyone copying this remembers to do it,
        # - we have overriden this in the DryadState object, so it doesn't do anything
        self.state.register_unthrottled_hit()
        
        # FIXME: we have to observe the Dryad interface for a bit to get a handle
        # on these response types - this is just a default approach...
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        # extract the aliases
        bibJSON = self._extract_biblio(response.text)
        biblio_object = Biblio(bibJSON)

        return biblio_object


    def _extract_biblio(self, xml):
        biblio_dict = {}

        try:
            title = self._get_named_arr_str_from_xml(xml, 'dc.title_ac')
            biblio_dict["title"] = title[0]
        except AttributeError:
            raise ProviderClientError(xml)

        try:
            year = self._get_named_arr_int_from_xml(xml, 'dc.date.accessioned.year')
            biblio_dict["year"] = year[0]
        except AttributeError:
            raise ProviderClientError(xml)

        return biblio_dict


class DryadState(ProviderState):
    def __init__(self, config):
        # need to init the ProviderState object counter
        if config.rate is not None:        
            super(DryadState, self).__init__(config.rate['period'], config['limit'])
        else:
            super(DryadState, self).__init__(throttled=False)
            
    def register_unthrottled_hit(self):
        # override this method, so it has no actual effect
        pass
        
  


