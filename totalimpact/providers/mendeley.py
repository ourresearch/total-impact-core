from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from totalimpact.providers.secrets import Mendeley_key

import simplejson, urllib

import logging
logger = logging.getLogger('providers.mendeley')

class Mendeley(Provider):  

    metric_names = [
        'mendeley:readers', 
        'mendeley:groups'
        ]

    metric_namespaces = ["doi"]
    alias_namespaces = ["doi"]
    biblio_namespaces = ["doi"]

    provides_members = False
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True

    everything_url_template = "http://api.mendeley.com/oapi/documents/details/%s?type=doi&consumer_key=" + Mendeley_key
    biblio_url_template = everything_url_template
    aliases_url_template = everything_url_template
    metrics_url_template = everything_url_template
    provenance_url_template = everything_url_template

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    def __init__(self):
        super(Mendeley, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = (namespace=="doi" or namespace=="pmid")
        return(relevant)

    #override because need to break up id
    def _get_templated_url(self, template, id, method=None):
        double_encoded_id = urllib.quote(urllib.quote(id, safe=""), safe="")
        query_url = template % double_encoded_id    
        return(query_url)

    def _extract_biblio(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        author_list = data["authors"]
        authors = ", ".join([author["surname"] for author in author_list])

        # extract the biblio
        biblio_dict = {
            'title' : data['title'],
            'year' : data['year'],
            'journal' : data['publication_outlet'],
            'authors' : authors
        }
        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        # extract the aliases
        aliases_list = [
                    ("url", data['website']), 
                    ('title', data['title'])]

        return aliases_list


    def _extract_metrics(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        metrics_dict = {
            'mendeley:readers' : data['stats']['readers'],
            'mendeley:groups' : len(data['groups'])
        }
        return metrics_dict

    # default method; providers can override    
    def provenance_url(self, metric_name, aliases):
        id = self.get_best_id(aliases)     
        if not id:
            # not relevant to Mendeley
            return None

        url = self._get_templated_url(self.provenance_url_template, id, "provenance")

        logger.debug("attempting to retrieve provenance url from " + url)
        # try to get a response from the data provider        
        response = self.http_get(url)
        if response.status_code != 200:
            # not in Mendeley database
            return None

        page = response.text
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        provenance_url = data['mendeley_url']
        return provenance_url
