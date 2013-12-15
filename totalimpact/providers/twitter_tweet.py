import os, re, datetime

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


    def screen_name(self, tweet_url):
        #regex from http://stackoverflow.com/questions/4424179/how-to-validate-a-twitter-username-using-regex
        match = re.findall("twitter.com/([A-Za-z0-9_]{1,15})/", tweet_url)
        return match[0]


    def tweet_id(self, tweet_url):
        match = re.findall("twitter.com/.*/status/(\d+)", tweet_url)
        return match[0]



    # default method; providers can override
    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        tweet_url = self.get_best_id(aliases)
        biblio_embed_url = self.biblio_template_url % (self.tweet_id(tweet_url))
        response = self.http_get(biblio_embed_url)
        data = provider._load_json(response.text)

        biblio_dict = {}
        biblio_dict["repository"] = "Twitter"
        biblio_dict["url"] = tweet_url

        if not data:
            return biblio_dict

        biblio_dict["title"] = u"@{screen_name}".format(screen_name=self.screen_name(tweet_url))
        biblio_dict["authors"] = data["author_name"]
        biblio_dict["embed"] = data["html"]
        biblio_dict["embed_url"] = biblio_embed_url
        biblio_dict["account"] = u"@{screen_name}".format(screen_name=self.screen_name(tweet_url))
        try:
            tweet_match = re.findall(u'<p>(.*?)</p>.*statuses/\d+">(.*?)</a></blockquote>', biblio_dict["embed"])
            biblio_dict["tweet_text"] = tweet_match[0][0]
            biblio_dict["date"] = datetime.datetime.strptime(tweet_match[0][1], "%B %d, %Y").isoformat()
            biblio_dict["year"] = biblio_dict["date"][0:4]
        except (AttributeError):
            logger.debug("couldn't parse tweet embed {embed}".format(
                embed=biblio_dict["embed"]))

        return biblio_dict
  

