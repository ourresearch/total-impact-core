from totalimpact.providers.provider import Provider

import simplejson, urllib

import logging
logger = logging.getLogger('providers.peerev')

class Peerev(Provider):  

    metric_names = ['peerev:views', 'peerev:downloads', 'peerev:comments', 'peerev:bookmarks']

    metric_names = [
        'peerev:views', 
        'peerev:downloads', 
        'peerev:comments', 
        'peerev:bookmarks'
        ]

    metric_namespaces = ["peerev"]

    provides_members = False
    provides_aliases = False
    provides_metrics = True
    provides_biblio = False

    everything_url_template = "http://peerev.surstar3.com/api/libraryID:%s"
    metrics_url_template = everything_url_template

    example_id = ("peerev", "23241")

    def __init__(self):
        super(Peerev, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (namespace=="peerev")
        return(relevant)

    #override because need to break up id
    def _get_templated_url(self, template, id, method=None):
        double_encoded_id = urllib.quote(urllib.quote(id, safe=""), safe="")
        query_url = template % double_encoded_id    
        return(query_url)

       
    def _extract_metrics(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        try:
            views = data['items'][0][0]['value']
        except KeyError:
            views = None

        try:
            downloads = data['items'][0][1]['value']
        except KeyError:
            downloads = None

        try:
            comments = data['items'][0][2]['value']
        except KeyError:
            comments = None

        try:
            bookmarks = data['items'][0][3]['value']
        except KeyError:
            bookmarks = None

        metrics_dict = {
            'mendeley:views' : views,
            'mendeley:downloads' : downloads,
            'mendeley:comments' : comments,
            'mendeley:bookmarks' : bookmarks
        }
        return metrics_dict

