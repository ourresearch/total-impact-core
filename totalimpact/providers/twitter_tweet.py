import os, re

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import logging
logger = logging.getLogger('ti.providers.twitter_tweet')

class Twitter_Tweet(Provider):  

    example_id = ("url", "http://twitter.com/jasonpriem")

    biblio_template_url = "https://api.twitter.com/1/statuses/oembed.json?id=%s&hide_media=1&hide_thread=1&maxwidth=650"
  

    def __init__(self):
        super(Twitter_Tweet, self).__init__()


    @property
    def provides_biblio(self):
         return True


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        try:
            nid = nid.lower()
        except AttributeError:
            return False 
        if (namespace == "url"):
            if ("twitter.com" in nid) and ("/status/" in nid):
                return True
        return False


    def screen_name(self, nid):
        #regex from http://stackoverflow.com/questions/4424179/how-to-validate-a-twitter-username-using-regex
        match = re.findall("twitter.com/([A-Za-z0-9_]{1,15})/", nid)
        return match[0]


    def tweet_id(self, nid):
        match = re.findall("twitter.com/.*/status/(\d+)", nid)
        return match[0]



    # default method; providers can override
    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        nid = self.get_best_id(aliases)
        url = self.biblio_template_url % (self.tweet_id(nid))
        response = self.http_get(url)
        data = provider._load_json(response.text)

        biblio_dict = {}
        biblio_dict["repository"] = "Twitter"

        if not data:
            return biblio_dict

        biblio_dict["title"] = u"@{screen_name}".format(screen_name=self.screen_name(nid))
        biblio_dict["authors"] = data["author_name"]
        biblio_dict["embed"] = data["html"]
        biblio_dict["account"] = u"@{screen_name}".format(screen_name=self.screen_name(nid))

        return biblio_dict
  

