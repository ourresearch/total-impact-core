import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Metrics, ProviderMetric, Aliases
from BeautifulSoup import BeautifulStoneSoup
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

    def _is_dryad_doi(self, alias):
        return self.dryad_doi_rx.search(alias[1]) is not None

    def _is_relevant_id(self, alias):
        return self._is_dryad_doi(alias)

    def _get_first_arr_str_from_xml(self, xml, name):
        identifiers = []

        soup = BeautifulStoneSoup(xml)
        try:
            arrs = soup.result.findAll("arr")
        except AttributeError:
            raise ProviderClientError(soup.text)
            
        for arr in arrs:
            # FIXME: this looks fragile.  Dependent on order of attributes
            # in supplied XML
            # FIXME: dc.identifier.uri is not in the arr.attrs, but
            # dc.identifier is.  Is this right or wrong?
            if (u'name', name) in arr.attrs:
                identifiers += [arr.str.text]
        return identifiers

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

        if (len(response.text) == 0):
            raise ProviderClientError(response)

        identifiers = self._get_first_arr_str_from_xml(response.text, "dc.identifier")

        return [(Aliases.NS.DOI, hit.replace("doi:", "")) for hit in list(set(identifiers))]

    
    def aliases(self, item): 
        # get the alias object
        alias_object = item.aliases
        logger.info(self.config.id + ": aliases requested for tiid:" + alias_object.tiid)
        
        # Get a list of the new aliases that can be discovered from the data
        # source
        new_aliases = []
        for alias in alias_object.get_aliases_list(self.config.supported_namespaces):
            if not self._is_dryad_doi(alias):
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
        
        # extract the aliases
        new_aliases = self._extract_aliases(response.text)
        if new_aliases is not None:
            logger.debug(self.config.id + ": found aliases: " + str(new_aliases))
            return new_aliases
        return []


    def _extract_aliases(self, xml):
        #print xml

        identifiers = []
        url_identifiers = self._get_first_arr_str_from_xml(xml, u'dc.identifier.uri')
        identifiers += [(Aliases.NS.URL, url) for url in url_identifiers]

        title_identifiers = self._get_first_arr_str_from_xml(xml, u'dc.title')
        identifiers += [(Aliases.NS.TITLE, title) for title in title_identifiers]

        return identifiers

    def provides_metrics(self): 
        return True
    
    def get_show_details_url(self, doi):
        return "http://dx.doi.org/" + doi

    def metrics(self, item):
        url = self.config.metrics['url'] % urllib.quote(item.id)
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


    def _extract_biblio(self, content):
        DRYAD_CITATION_PATTERN = re.compile('please cite the Dryad data package:.*<blockquote>(?P<authors>.+?)\((?P<year>\d{4})\).*(?P<title>Data from.+?)<span>Dryad', re.DOTALL)
        citation_matches = DRYAD_CITATION_PATTERN.search(content)
        try:
            authors = citation_matches.group("authors")
            year = citation_matches.group("year")
            title = citation_matches.group("title")
        except ValueError:
            authors = None
            year = None
            title = None
        return({"title":title, "year":year, "authors":authors})


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
        
  


