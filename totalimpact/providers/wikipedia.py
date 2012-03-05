from provider import Provider
from model import Metrics
from http_layer import
from BeautifulSoup import BeautifulStoneSoup

class Wikipedia(Provider):

    WIKIPEDIA_API_URL = 'http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch="%s"'
    
    def __init__(self):
        pass
    
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
            
    def _get_metrics(self, alias, metrics):
        url = self.WIKIPEDIA_API_URL % doi
        response, content = self.http_get(url)
        this_metrics = Metrics()
        self.extract_stats(content, this_metrics)
        self.show_details_url('http://en.wikipedia.org/wiki/Special:Search?search="' + artifact_id + '"&go=Go', this_metrics)
        metrics.add_metrics(this_metrics)
        
    def extract_stats(self, content, metrics):
        soup = BeautifulStoneSoup(content)
        try:
            articles = soup.search.findAll(title=True)
            metrics.add("mentions", len(articles))
        except AttributeError:
            # doesn't matter
            pass