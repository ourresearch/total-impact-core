from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os, re
from bs4 import BeautifulSoup

import logging
logger = logging.getLogger('ti.providers.github_account')

class Github_Account(Provider):  

    example_id = ("github", "egonw,cdk")

    url = "http://github.com"
    descr = "A social, online repository for open-source software."
    member_items_url_template = "https://api.github.com/users/%s/repos?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    biblio_url_template = "https://api.github.com/users/%s?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    aliases_url_template = "https://api.github.com/users/%s?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    metrics_url_template = "https://api.github.com/users/%s?client_id=" + os.environ["GITHUB_CLIENT_ID"] + "&client_secret=" + os.environ["GITHUB_CLIENT_SECRET"]
    repo_url_template = "https://github.com/%s/%s"

    provenance_url_template = "https://github.com/%s"

    static_meta_dict = {
        "followers": {
            "display_name": "followers",
            "provider": "GitHub",
            "provider_url": "http://github.com",
            "description": "The number of people who have given the GitHub repository a star",
            "icon": "https://github.com/fluidicon.png",
        },
        "joined_date": {
            "display_name": "forks",
            "provider": "GitHub",
            "provider_url": "http://github.com",
            "description": "The number of people who have forked the GitHub repository",
            "icon": "https://github.com/fluidicon.png",
            }
    }     

    def __init__(self):
        super(Github_Account, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if (namespace != "url"):
            return False
        if re.match(".+github.com/.+/.+", nid):
            return False
        if re.match(".+github.com/.+", nid):
            return True
        return False


    @property
    def provides_biblio(self):
         return True

    @property
    def provides_metrics(self):
         return True

    #override because need to break up id
    def _get_templated_url(self, template, id, method=None):
        if "http" in id:
            (host, username) = id.rsplit("/", 1)
        url = template % username
        return(url)


    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True): 

        id = self.get_best_id(aliases)
                   
        biblio_dict = {}
        biblio_dict["repository"] = "GitHub"
        biblio_dict["is_account"] = True
        biblio_dict["genre"] = "account"
        biblio_dict["account"] = id
        return biblio_dict   
   
    def _extract_metrics_from_api_users(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "followers" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'github_account:followers' : ['followers'],
            'github_account:number_repos' : ['public_repos'],
            'github_account:number_gists' : ['public_gists'],
            'github_account:joined_date' : ['created_at']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict


    def _extract_metrics_from_github_webpage(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        metrics_dict = {}
        soup = BeautifulSoup(page)
        orgs_match = soup.find("h3", text="Organizations")
        if orgs_match:
            org_links = orgs_match.parent.find_all("a")
            orgs_list = [org_link.get("aria-label") for org_link in org_links]
            if orgs_list:
                orgs = ", ".join(orgs_list)
                metrics_dict.update({"github_account:organizations": orgs})

        contrib_match = soup.find("div", attrs={"class", "contrib-details"})
        if contrib_match:
            num_contribs_match_div = contrib_match.find("div", attrs={"class", "contrib-day"})
            num_contribs_match_span = num_contribs_match_div.find("span", attrs={"class", "num"})
            num_contributions_match = re.search("(\d+)", repr(num_contribs_match_span))
            metrics_dict.update({"github_account:number_contributions": int(num_contributions_match.group(1))})

            longest_streak_match_div = contrib_match.find("div", attrs={"class", "contrib-streak"})
            longest_streak_match_span = longest_streak_match_div.find("span", attrs={"class", "num"})
            longest_streak_match = re.search("(\d+)", repr(longest_streak_match_span))
            metrics_dict.update({"github_account:longest_streak_days": int(longest_streak_match.group(1))})

        return metrics_dict


    def _extract_metrics_from_open_source_report_card(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "repositories" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'github_account:active_repos' : ['repositories'],
            'github_account:languages' : ["usage", 'languages']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)
        return metrics_dict


    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_metrics:
            raise NotImplementedError()

        id = self.get_best_id(aliases)

        # Only lookup metrics for items with appropriate ids
        if not id:
            #self.logger.debug(u"%s not checking metrics, no relevant alias" % (self.provider_name))
            return {}

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        extract_templates = {
            self.metrics_url_template: self._extract_metrics_from_api_users,
            "https://github.com/%s" : self._extract_metrics_from_github_webpage,
            "https://osrc.dfm.io/%s.json": self._extract_metrics_from_open_source_report_card
        }

        metrics = {}
        for template in extract_templates:
            new_metrics = self.get_metrics_for_id(id, 
                    provider_url_template=template, 
                    cache_enabled=cache_enabled, 
                    extract_metrics_method=extract_templates[template])
            if new_metrics:
                metrics.update(new_metrics)

        metrics_and_drilldown = {}
        for metric_name in metrics:
            drilldown_url = self.provenance_url(metric_name, aliases)
            metrics_and_drilldown[metric_name] = (metrics[metric_name], drilldown_url)

        return metrics_and_drilldown  




