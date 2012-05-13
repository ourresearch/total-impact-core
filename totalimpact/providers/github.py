from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson

import logging
logger = logging.getLogger('providers.github')

class Github(Provider):  

    metric_names = [
        'github:watchers', 
        'github:forks'
        ]

    metric_namespaces = ["github"]
    alias_namespaces = ["github"]
    biblio_namespaces = ["github"]

    provides_members = True
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True

    member_items_url_template = "https://api.github.com/users/%s/repos"
    biblio_url_template = "https://github.com/api/v2/json/repos/show/%s"
    aliases_url_template = "https://github.com/api/v2/json/repos/show/%s"
    metrics_url_template = "https://github.com/api/v2/json/repos/show/%s"

    example_id = ("github", "egonw")

    def __init__(self):
        super(Github, self).__init__()

    def get_github_id(self, aliases):
        matching_id = None
        for alias in aliases:
            if alias:
                (namespace, id) = alias
                if namespace == "github":
                    matching_id = id[0]
        print aliases, matching_id
        return matching_id

    def get_best_id(self, aliases):
        return self.get_github_id(aliases)

    def known_aliases(self, aliases):
        return [self.get_github_id(aliases)]

    def _is_relevant_id(self, alias):
        return("github" == alias[0])

    def _extract_members(self, page, query_string):
        try:
            hits = simplejson.loads(page)
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        hits = [hit["name"] for hit in hits]
        members = [("github", (query_string, hit)) for hit in list(set(hits))]
        return(members)

    def _extract_biblio(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        # extract the biblio
        biblio_dict = {
            'title' : data['repository']['name'],
            'description' : data['repository']['description'],
            'owner' : data['repository']['owner'],
            'url' : data['repository']['url'],
            'last_push_date' : data['repository']['pushed_at'],
            'create_date' : data['repository']['created_at']
        }

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError
        
        # extract the aliases
        aliases_list = [
                    ("url", data['repository']['url']), 
                    ("title", data['repository']['name'])]

        return aliases_list

    def _extract_metrics(self, page, id=None):
        try:
            data = simplejson.loads(page) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        metrics_dict = {
            'github:watchers' : data['repository']['watchers'],
            'github:forks' : data['repository']['forks']
        }

        return metrics_dict

