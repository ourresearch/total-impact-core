import time, re, urllib
from provider import Provider, ProviderError, ProviderTimeout, ProviderServerError, ProviderClientError, ProviderHttpError, ProviderState
from totalimpact.models import Metrics, ProviderMetric
from BeautifulSoup import BeautifulStoneSoup
import requests

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

class DryadMetricSnapshot(ProviderMetric):
    def __init__(self):
        super(DryadMetricSnapshot, self).__init__()

class Dryad(Provider):  

    def __init__(self, config, app_config):
        super(Dryad, self).__init__(config, app_config)
        self.state = DryadState(config)
        self.id = self.config.id
        
        # All CrossRef DOI prefixes begin with "10" followed by a number of four or more digits
        # from http://www.crossref.org/02publishers/doi-guidelines.pdf
        # DOI_PATTERN = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)
        # CROSSREF_DOI_PATTERN = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)
        self.crossref_rx = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)
        self.dryad_member_items_rx = re.compile(r"(10\.5061/.*)</span")

    def member_items(self, query_string):
        # FIXME: only checks the first dryad page
        enc = urllib.quote(query_string)
        url = self.config.member_items['url'] % enc
        logger.debug(self.config.id + ": attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=self.config.member_items.get('timeout', None))
        hits = self.dryad_member_items_rx.findall(response.text)
        return [("DOI", hit) for hit in list(set(hits))]
    
    def aliases(self, item): 
        try:
            # get the alias object
            alias_object = item.aliases
            logger.info(self.config.id + ": aliases requested for tiid:" + alias_object.tiid)
            
            # Get a list of the new aliases that can be discovered from the data
            # source
            new_aliases = []
            for alias in alias_object.get_aliases_list(self.config.supported_namespaces):
                if not self._is_crossref_doi(alias):
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
        except ProviderError as e:
            self.error(e, item)
            return item
        

    def _is_crossref_doi(self, alias):
        # FIXME: Would exclude DataCite ids from here?
        return self.crossref_rx.search(alias[1]) is not None

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
        soup = BeautifulStoneSoup(xml)
        try:
            identifier = soup.result.doc.arr.str.string
            if identifier.lower().startswith("doi:"):
                identifier = identifier[4:]
            
            # FIXME: we need a namespace table
            return [("DOI", identifier)]
        except AttributeError:
            return None

    def provides_metrics(self): 
        return True
    
    def get_show_details_url(self, doi):
        return "http://dx.doi.org/" + doi

    def metrics(self, item):
        raise NotImplementedError()
        return ("1")      

    def _extract_stats(self, content):
        DRYAD_VIEWS_PACKAGE_PATTERN = re.compile("(?P<views>\d+) views</span>", re.DOTALL)
        DRYAD_VIEWS_FILE_PATTERN = re.compile("(?P<views>\d+) views\S", re.DOTALL)
        DRYAD_DOWNLOADS_PATTERN = re.compile("(?P<downloads>\d+) downloads", re.DOTALL)
        DRYAD_CITATION_PATTERN = re.compile('please cite the Dryad data package:.*<blockquote>(?P<authors>.+?)\((?P<year>\d{4})\).*(?P<title>Data from.+?)<span>Dryad', re.DOTALL)

        view_matches_package = DRYAD_VIEWS_PACKAGE_PATTERN.finditer(content)
        view_matches_file = DRYAD_VIEWS_FILE_PATTERN.finditer(content)
        try:
            view_package = max([int(view_match.group("views")) for view_match in view_matches_package])
            file_total_views = sum([int(view_match.group("views")) for view_match in view_matches_file]) - view_package
        except ValueError:
            max_views = None
            total_views = None
        
        download_matches = DRYAD_DOWNLOADS_PATTERN.finditer(content)
        try:
            downloads = [int(download_match.group("downloads")) for download_match in download_matches]
            total_downloads = sum(downloads)
            max_downloads = max(downloads)
        except ValueError:
            total_downloads = None
            max_downloads = None

        citation_matches = DRYAD_CITATION_PATTERN.search(content)
        try:
            authors = citation_matches.group("authors")
            year = citation_matches.group("year")
            title = citation_matches.group("title")
        except ValueError:
            authors = None
            year = None
            title = None
                
        return({"file_views":file_total_views, "package_views":view_package, "total_downloads":total_downloads, "most_downloaded_file":max_downloads, "title":title, "year":year, "authors":authors})


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
        
  


