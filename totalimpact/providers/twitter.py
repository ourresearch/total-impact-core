import os, re

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderRateLimitError
from totalimpact.providers.twitter_paging import TwitterPager
from birdy.twitter import AppClient
from birdy.twitter import TwitterApiError, TwitterRateLimitError, TwitterClientError

import logging
logger = logging.getLogger('ti.providers.twitter')

class Twitter(Provider):  

    example_id = ("url", "http://twitter.com/jasonpriem")

    url = "http://twitter.com"
    descr = "Social networking and microblogging service."
    member_items_url_template = "http://twitter.com/%s"
    provenance_url_templates = {
        "twitter:followers": "https://twitter.com/%s/followers",
        "twitter:lists": "https://twitter.com/%s/memberships",
        "twitter:number_tweets": "https://twitter.com/%s"
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
            },
        "number_tweets": {
            "display_name": "number of tweets",
            "provider": "Twitter",
            "provider_url": "http://twitter.com",
            "description": "The number of tweets from this Twitter account",
            "icon": "https://twitter.com/favicon.ico"
            }            
    }     

    def __init__(self):
        super(Twitter, self).__init__()
        self.client = AppClient(os.getenv("TWITTER_CONSUMER_KEY"), 
                            os.getenv("TWITTER_CONSUMER_SECRET"),
                            os.getenv("TWITTER_ACCESS_TOKEN"))


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
        return(members)

    
    def get_account_data(self, aliases, number_tweets=20, max_pages=1):
        nid = self.get_best_id(aliases)
        if not nid:
            return None

        response_list = []
        def save_to_list(r):
            if r.data:
                response_list.extend(r.data)

        pager = TwitterPager(os.getenv("TWITTER_CONSUMER_KEY"), 
                        os.getenv("TWITTER_CONSUMER_SECRET"),
                        os.getenv("TWITTER_ACCESS_TOKEN"), 
                        default_max_pages=max_pages)

        try:
            r = pager.paginated_search(
                page_handler=save_to_list,
                screen_name=self.screen_name(nid), 
                count=number_tweets, 
                contributor_details=True, 
                include_rts=True,
                exclude_replies=False,
                trim_user=False
                )
        except TwitterApiError:
            logger.error("TwitterApiError error, skipping")
            return None
        except TwitterClientError:
            logger.error("TwitterClientError error, skipping")
            return None
        return response_list   


    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        biblio_dict = {}
        biblio_dict["repository"] = "Twitter"

        data_list = self.get_account_data(aliases, number_tweets=1)
        if not data_list:
            return biblio_dict

        data = data_list[0]["user"]

        twitter_username = data["screen_name"]
        twitter_username_with_at = u"@{twitter_username}".format(
            twitter_username=twitter_username)
        biblio_dict["title"] = twitter_username_with_at
        biblio_dict["authors"] = data["name"]
        biblio_dict["description"] = data["description"]
        biblio_dict["created_at"] = data["created_at"]
        biblio_dict["url"] = u"http://twitter.com/{twitter_username}".format(
            twitter_username=twitter_username)

        biblio_dict["is_account"] = True  # special key to tell webapp to render as genre heading
        biblio_dict["account"] = twitter_username_with_at
        biblio_dict["genre"] = "account"

        return biblio_dict
  


    def metrics(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        data_list = self.get_account_data(aliases, number_tweets=1)
        if not data_list:
            return {}
        data = data_list[0]["user"]

        dict_of_keylists = {
            'twitter:followers' : ['followers_count'],
            'twitter:lists' : ['listed_count'],
            'twitter:number_tweets' : ['statuses_count']
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



     

