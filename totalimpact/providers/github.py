from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os, re

import logging
logger = logging.getLogger('ti.providers.github')

class Github(Provider):  

    example_id = ("github", "egonw,cdk")

    url = "http://github.com"
    descr = "A social, online repository for open-source software."
    member_items_url_template = "https://api.github.com/users/%s/repos?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    biblio_url_template = "https://api.github.com/repos/%s/%s?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    aliases_url_template = "https://api.github.com/repos/%s/%s?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    metrics_url_template = "https://api.github.com/repos/%s/%s?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    repo_url_template = "https://github.com/%s/%s"
    account_url_template = "https://github.com/%s"

    provenance_url_templates = {
        "github:stars" : "https://github.com/%s/%s/stargazers",
        "github:forks" : "https://github.com/%s/%s/network/members"
        }

    static_meta_dict = {
        "stars": {
            "display_name": "stars",
            "provider": "GitHub",
            "provider_url": "http://github.com",
            "description": "The number of people who have given the GitHub repository a star",
            "icon": "https://github.com/fluidicon.png",
        },
        "forks": {
            "display_name": "forks",
            "provider": "GitHub",
            "provider_url": "http://github.com",
            "description": "The number of people who have forked the GitHub repository",
            "icon": "https://github.com/fluidicon.png",
            }
    }     

    def __init__(self):
        super(Github, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = ((namespace=="url") and re.match(".+github.com/.+/.+", nid))
        return(relevant)

    #override because need to break up id
    def _get_templated_url(self, template, nid, method=None):
        url = None
        if method=="members":
            url = template % nid
        else:
            if "http" in nid:
                (host, username, repo_name) = nid.rsplit("/", 2)
            else:
                (username, repo_name) = nid.split(",")  # deprecate github namespace after /v1
            url = template % (username, repo_name)

        return(url)

    def _extract_members(self, page, account_name): 
        members = []
        # add repositories from account
        data = provider._load_json(page)
        repos = [repo["name"] for repo in data]
        members += [("url", self.repo_url_template %(account_name, repo)) for repo in list(set(repos))]

        # also add account product!
        members += [("url", self.account_url_template %(account_name))]

        return(members)


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['name'],
            'description' : ['description'],
            'owner' : ['owner', 'login'],
            'url' : ['svn_url'],
            'last_push_date' : ['pushed_at'],
            'create_date' : ['created_at']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)
        try:
            biblio_dict["year"] = biblio_dict["create_date"][0:4]
        except KeyError:
            pass
        biblio_dict["repository"] = "GitHub"

        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"url": ["svn_url"], 
                            "title" : ["name"]}

        aliases_dict = provider._extract_from_json(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "forks_count" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'github:stars' : ['watchers'],
            'github:forks' : ['forks']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict


    # overriding default because different provenance url for each metric
    def provenance_url(self, metric_name, aliases):
        nid = self.get_best_id(aliases)
        if not nid:
            return None
        provenance_url = self._get_templated_url(self.provenance_url_templates[metric_name], nid, "provenance")
        return provenance_url
