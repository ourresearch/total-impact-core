from birdy.twitter import AppClient, TwitterApiError
import os, re

from totalimpact.providers import provider
from totalimpact.providers import topsy
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import logging
logger = logging.getLogger('ti.providers.twitter_account')

class Twitter_Account(Provider):  

    example_id = ("url", "http://twitter.com/jasonpriem")

    url = "http://twitter.com"
    descr = "Social networking and microblogging service."
    member_items_url_template = "http://twitter.com/%s"
    provenance_url_templates = {
        "twitter_account:followers": "https://twitter.com/%s/followers",
        "twitter_account:lists": "https://twitter.com/%s/memberships"
        }

    static_meta_dict = {
        "followers": {
            "display_name": "followers",
            "provider": "Twitter",
            "provider_url": "http://twitter.com",
            "description": "The number of people following this Twitter account",
            "icon": "https://twitter.com/favicon.ico"
        },
        "lists": {
            "display_name": "lists",
            "provider": "Twitter",
            "provider_url": "http://twitter.com",
            "description": "The number of people who have included this Twitter account in a Twitter list",
            "icon": "https://twitter.com/favicon.ico"
            }
    }     

    def __init__(self):
        super(Twitter_Account, self).__init__()
        self.client = AppClient(os.getenv("TWITTER_CONSUMER_KEY"), 
                            os.getenv("TWITTER_CONSUMER_SECRET"),
                            os.getenv("TWITTER_ACCESS_TOKEN"))

    # overriding default because overriding member_items method
    @property
    def provides_members(self):
        return True

    @property
    def provides_biblio(self):
         return True

    @property
    def provides_metrics(self):
         return True


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        try:
            nid = nid.lower()
        except AttributeError:
            return False 
        if (namespace == "url"):
            if ("twitter.com" in nid) and ("/status/" not in nid):
                return True
        return False


    def screen_name(self, nid):
        #regex from http://stackoverflow.com/questions/4424179/how-to-validate-a-twitter-username-using-regex
        match = re.findall("twitter.com/([A-Za-z0-9_]{1,15}$)", nid)
        return match[0]


    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        twitter_username = query_string.replace("@", "")
        url = self._get_templated_url(self.member_items_url_template, twitter_username, "members")
        members = [("url", url)]

        for tweet_url in topsy.Topsy().top_tweeted_urls(twitter_username, "twitter_account", number_to_return=25):
            members += [("url", tweet_url)] 

        return(members)


    def get_account_data(self, aliases):
        nid = self.get_best_id(aliases)
        if not nid:
            return None

        try:
            screen_name = self.screen_name(nid)
            r = self.client.api.users.show.get(screen_name=screen_name)
        except (IndexError, TwitterApiError):
            return None

        return r.data



    # default method; providers can override
    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        biblio_dict = {}
        biblio_dict["repository"] = "Twitter"

        data = self.get_account_data(aliases)
        if not data:
            return biblio_dict

        biblio_dict["title"] = u"@{screen_name}".format(
            screen_name=data["screen_name"])
        biblio_dict["authors"] = data["name"]
        biblio_dict["description"] = data["description"]
        biblio_dict["created_at"] = data["created_at"]

        return biblio_dict
  


    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        data = self.get_account_data(aliases)
        if not data:
            return {}

        dict_of_keylists = {
            'twitter_account:followers' : ['followers_count'],
            'twitter_account:lists' : ['listed_count']
        }

        metrics_dict = {}
        for field in dict_of_keylists:
            metric_value = data[dict_of_keylists[field][0]]
            if metric_value:
                metrics_dict[field] = metric_value

        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self.provenance_url(metric_name, aliases)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)

        return metrics_and_drilldown  


    # overriding default because different provenance url for each metric
    def provenance_url(self, metric_name, aliases):
        nid = self.get_best_id(aliases)
        if not nid:
            return None
        screen_name = self.screen_name(nid)
        provenance_url = self._get_templated_url(self.provenance_url_templates[metric_name], screen_name, "provenance")
        return provenance_url


