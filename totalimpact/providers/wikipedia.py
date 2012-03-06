from provider import Provider
from model import Metrics
from BeautifulSoup import BeautifulStoneSoup

class Wikipedia(Provider):

    
    def sleep_time(self):
        return 5
    
    def member_items(self, query_string): 
        raise NotImplementedError()
    
    def aliases(self, alias_object): 
        raise NotImplementedError()
        
    def metrics(self, alias_object):
        metrics = Metrics()
        for alias in alias_object.aliases:
            if not self._is_supported(alias):
                continue
            self._get_metrics(alias, metrics)
        return metrics
    
    def _is_supported(self, alias):
        return alias[0] in self.config.supported_namespaces
    
    def _get_metrics(self, alias, metrics):
        url = self.config.url.metrics.replace("[ID]", alias[1])
        response = self.http_get(url)
        this_metrics = Metrics()
        self._extract_stats(response.content, this_metrics)
        self.show_details_url('http://en.wikipedia.org/wiki/Special:Search?search="' + alias[1] + '"&go=Go', this_metrics)
        metrics.add_metrics(this_metrics)
        
    def _extract_stats(self, content, metrics):
        soup = BeautifulStoneSoup(content)
        try:
            articles = soup.search.findAll(title=True)
            metrics.add("mentions", len(articles))
        except AttributeError:
            # doesn't matter
            pass