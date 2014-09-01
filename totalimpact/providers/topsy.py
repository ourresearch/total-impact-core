from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import json, re, os
from operator import itemgetter

import logging
logger = logging.getLogger('ti.providers.topsy')

class Topsy(Provider):  

    example_id = ("url", "http://total-impact.org")

    url = "http://www.topsy.com/"
    descr = "Real-time search for the social web, <a href='http://topsy.com'><img src='http://cdn.topsy.com/img/powered.png'/></a>"
    metrics_url_template_general = 'http://otter.topsy.com/stats.json?url=%s&window=a&apikey=' + os.environ["TOPSY_KEY"]
    metrics_url_template_site = 'http://otter.topsy.com/search.json?q=site:%s&window=a&page=1&perpage=100&apikey=' + os.environ["TOPSY_KEY"]

    provenance_url_template_general = 'http://topsy.com/trackback?url=%s&window=a'
    provenance_url_template_site = 'http://topsy.com/s?q=site%%3A%s&window=a'  #escape % with %%

    top_tweeted_url_templates = {
        "site": 'http://otter.topsy.com/search.json?q=site:%s&window=a&type=link&page=%s&perpage=100&apikey=' + os.environ["TOPSY_KEY"],
        "twitter_account": 'http://otter.topsy.com/search.json?q=@%s&window=a&type=tweet&page=%s&perpage=100&apikey=' + os.environ["TOPSY_KEY"],
        "tweets_about": 'http://otter.topsy.com/search.json?q=@%s&window=a&type=tweet&page=%s&perpage=100&apikey=' + os.environ["TOPSY_KEY"]
    }

    static_meta_dict =  {
        "tweets": {
            "display_name": "tweets",
            "provider": "Topsy",
            "provider_url": "http://www.topsy.com/",
            "description": "Number of times the item has been tweeted",
            "icon": "http://twitter.com/phoenix/favicon.ico",
        },    
        "influential_tweets": {
            "display_name": "influential tweets",
            "provider": "Topsy",
            "provider_url": "http://www.topsy.com/",
            "description": "Number of times the item has been tweeted by influential tweeters",
            "icon": "http://twitter.com/phoenix/favicon.ico" ,
        }
    }
    

    def __init__(self):
        super(Topsy, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return namespace in ["blog", "url"]

    @property
    def provides_metrics(self):
         return True

    def get_site_id_for_template(self, aliases):
        for alias in aliases:
            (namespace, nid) = alias
            if ("blog"==namespace):
                blog_url_for_template = provider.strip_leading_http(nid).lower()
                return blog_url_for_template
        return None

    def get_best_id(self, aliases):
        nid = self.get_site_id_for_template(aliases)
        if nid:
            return nid
        else:
            metrics_url_template = self.metrics_url_template_general
            return self.get_relevant_alias_with_most_metrics("topsy:tweets", aliases, metrics_url_template)


    def provenance_url(self, metric_name, aliases):
        nid = self.get_site_id_for_template(aliases)
        if nid:
            provenance_url_template = self.provenance_url_template_site
        else:
            provenance_url_template = self.provenance_url_template_general
            metrics_url_template = self.metrics_url_template_general
            nid = self.get_relevant_alias_with_most_metrics("topsy:tweets", aliases, metrics_url_template)

        drilldown_url = self._get_templated_url(provenance_url_template, nid)
        return drilldown_url


    def metrics(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        metrics_and_drilldown = {}
        nid = self.get_site_id_for_template(aliases)
        if nid:
            metrics_url_template = self.metrics_url_template_site
        else:
            metrics_url_template = self.metrics_url_template_general
            nid = self.get_relevant_alias_with_most_metrics("topsy:tweets", aliases, metrics_url_template, cache_enabled)

        if not nid:
            return {}
            
        metrics = self.get_metrics_for_id(nid, metrics_url_template, cache_enabled)
        metrics_and_drilldown = {}
        for metric_name in metrics:
            drilldown_url = self.provenance_url(metric_name, aliases)
            metrics_and_drilldown[metric_name] = (metrics[metric_name], drilldown_url)

        return metrics_and_drilldown 


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        metrics_dict = {}

        if "hits" in page:
            data = provider._load_json(page)
            hits = [post["hits"] for post in data["response"]["list"]]
            if hits:
                sum_of_hits = sum(hits)
                metrics_dict["topsy:tweets"] = sum_of_hits
        else:
            dict_of_keylists = {
                'topsy:tweets' : ['response', 'all'],
                'topsy:influential_tweets' : ['response', 'influential']
            }
            metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        return metrics_dict


    def get_url_from_entry(self, query, entry, query_type):
        if query_type=="site":
            if query.lower() in entry["url"].lower():
                return entry["url"]
            elif entry["url_expansions"] and ("topsy_expanded_url" in entry["url_expansions"][0].lower()):
                return entry["url_expansions"][0]["topsy_expanded_url"]
        elif query_type=="twitter":
            if "/{query}/".format(query=query.lower()) in entry["url"].lower():
                return entry["url"]
            else:
                return None
        elif query_type=="tweets_about":
            if "/{query}/".format(query=query.lower()) not in entry["url"].lower():
                return entry["url"]
            else:
                return None
        return entry["url"]


    def top_tweeted_urls(self, query, query_type="site", number_to_return=10, pages=5):

        if query_type == "site":
            query = re.sub("http(s?)://", "", query.lower())
        elif query_type in ["twitter", "tweets_about"]:
            query = query.replace("@", "")

        template_url = self.top_tweeted_url_templates[query_type]
        urls = [template_url % (query, i) for i in range(1, pages+1)]
        responses = self.http_get_multiple(urls)
        tweeted_entries = [] 
        for url in responses:
            tweeted_entries += provider._load_json(responses[url].text)["response"]["list"]
        sorted_list = sorted(tweeted_entries, key=itemgetter('hits'), reverse=True) 

        top_tweeted_urls = [] #needs to be ordered

        for entry in sorted_list:
            url = self.get_url_from_entry(query, entry, query_type)
            if url and (url not in top_tweeted_urls):
                top_tweeted_urls.append(url)    
        return(top_tweeted_urls[0:number_to_return])

