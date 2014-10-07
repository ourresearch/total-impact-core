from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import json, re, os, requests, socket
from operator import itemgetter

import logging
logger = logging.getLogger('ti.providers.altmetric_com')

class Altmetric_Com(Provider):  

    example_id = ("doi", "10.1101/gr.161315.113")

    url = "http://www.altmetric.com"
    descr = "We make article level metrics easy."
    aliases_url_template = 'http://api.altmetric.com/v1/fetch/%s?key=' + os.environ["ALTMETRIC_COM_KEY"]
    metrics_url_template_via_fetch = 'http://api.altmetric.com/v1/fetch/id/%s?key=' + os.environ["ALTMETRIC_COM_KEY"]
    metrics_url_template_via_citations = 'http://api.altmetric.com/v1/citations/1y?key=' + os.environ["ALTMETRIC_COM_KEY"]
    provenance_url_template = 'http://www.altmetric.com/details.php?citation_id=%s&src=impactstory.org'

    static_meta_dict =  {
        "tweets": {
            "display_name": "Twitter tweets",
            "provider": "Altmetric.com",
            "provider_url": "http://twitter.com",
            "description": "Number of times the product has been tweeted",
            "icon": "https://twitter.com/favicon.ico",
        },
        "facebook_posts": {
            "display_name": "Facebook public posts",
            "provider": "Altmetric.com",
            "provider_url": "http://facebook.com",
            "description": "Number of posts mentioning the product on a public Facebook wall",
            "icon": "http://facebook.com/favicon.ico",
        },
        "gplus_posts": {
            "display_name": "Google+ posts",
            "provider": "Altmetric.com",
            "provider_url": "http://plus.google.com",
            "description": "Number of posts mentioning the product on Google+",
            "icon": "http://plus.google.com/favicon.ico",
        },
        "blog_posts": {
            "display_name": "blog posts",
            "provider": "Altmetric.com",
            "provider_url": "",
            "description": "Number of blog posts mentioning the product",
            "icon": "http://impactstory.org/static/img/blogs-icon.png",
        },
        # "news": {
        #     "display_name": "News outlets",
        #     "provider": "Altmetric.com",
        #     "provider_url": "",
        #     "description": "Number of mainstream media news mentions of the product",
        #     "icon": "",
        # },
        "impressions": {
            "display_name": "Twitter impressions",
            "provider": "Altmetric.com",
            "provider_url": "http://twitter.com",
            "description": "Number of times a tweet about the product has appeared in someone's twitter stream",
            "icon": "https://twitter.com/favicon.ico",
        }                                                   
    }
    

    def __init__(self):
        super(Altmetric_Com, self).__init__()

    @property
    def provides_aliases(self):
        return True

    @property
    def provides_metrics(self):
        return True

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return namespace in ["doi"]

    def get_best_id(self, aliases):
        # return it with the id type as a prefix before / because that's how the altmetric.com api expects it
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "altmetric_com" in aliases_dict:
            best_id = aliases_dict["altmetric_com"][0]
        else:
            best_id = None
        return(best_id)


    def provenance_url(self, metric_name, aliases):
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        try:
            drilldown_url = self._get_templated_url(self.provenance_url_template, aliases_dict["altmetric_com"][0])
        except KeyError:
            drilldown_url = ""
        return drilldown_url


    def get_id_for_aliases(self, aliases):
        # return it with the id type as a prefix before / because that's how the altmetric.com api expects it
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "doi" in aliases_dict:
            best_id = "doi/{id}".format(id=aliases_dict["doi"][0])
        elif "pmid" in aliases_dict:
            best_id = "pmid/{id}".format(id=aliases_dict["pmid"][0])
        elif "arxiv" in aliases_dict:
            best_id = "arxiv_id/{id}".format(id=aliases_dict["arxiv"][0])
        elif "altmetric_com" in aliases_dict:
            best_id = "altmetric_com/{id}".format(id=aliases_dict["altmetric_com"][0])
        else:
             best_id = None
        return(best_id)


    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        aliases_dict = provider.alias_dict_from_tuples(aliases)

        if "altmetric_com" in aliases_dict:
            return []  # nothing new to add

        nid = self.get_id_for_aliases(aliases)
        if not nid:
            return []

        new_aliases = self._get_aliases_for_id(nid, provider_url_template, cache_enabled)
        return new_aliases


    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {"altmetric_com": ["altmetric_id"]}

        aliases_dict = provider._extract_from_json(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [("altmetric_com", str(aliases_dict["altmetric_com"]))]
        else:
            aliases_list = []
        return aliases_list


    def _extract_metrics_via_fetch(self, page, status_code=200, id=None):
        dict_of_keylists = {
            'altmetric_com:tweets' : ['counts', 'twitter', 'posts_count'],
            'altmetric_com:unique_tweeters' : ['counts', 'twitter', 'unique_users_count'],
            # 'altmetric_com:news' : ['counts', 'news', 'posts_count'],
            # 'altmetric_com:unique_news' : ['counts', 'news', 'unique_users_count'],
            # 'altmetric_com:news_names' : ['counts', 'news', 'unique_users'],
            'altmetric_com:demographics' : ['demographics'],
            'altmetric_com:posts' : ['posts']
        }
        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        try:
            if metrics_dict['altmetric_com:posts'] and "twitter" in metrics_dict['altmetric_com:posts']:
                twitter_posts = metrics_dict['altmetric_com:posts']["twitter"]
                impressions = 0
                tweeter_followers = []
                for post in twitter_posts:
                    # print post["author"]
                    twitter_handle = post["author"]["id_on_source"]
                    try:
                        followers = post["author"]["followers"]
                        tweeter_followers.append([twitter_handle, followers])
                    except KeyError:
                        pass
                impressions = sum([followers for (handle, followers) in tweeter_followers])
                if tweeter_followers:
                    metrics_dict['altmetric_com:tweeter_followers'] = tweeter_followers
                if impressions:
                    metrics_dict['altmetric_com:impressions'] = impressions
        except KeyError:
            pass  # no posts

        return metrics_dict


    def _extract_metrics_for_via_citation_call(self, data, status_code=200, id=None):
        dict_of_keylists = {
            'altmetric_com:gplus_posts' : ['cited_by_gplus_count'],
            'altmetric_com:facebook_posts' : ['cited_by_fbwalls_count'],
            'altmetric_com:blog_posts' : ['cited_by_feeds_count']
        }
        entry = data["results"][0]
        metrics_dict = provider._extract_from_data_dict(entry, dict_of_keylists)
        return metrics_dict


    def get_metrics_for_via_citation_call(self, 
            id, 
            provider_url_template=None, 
            cache_enabled=True):

        # self.logger.debug(u"%s getting metrics for %s" % (self.provider_name, id))

        headers = {u'content-type': u'application/x-www-form-urlencoded',
                    u'accept': u'application/json'}

        r = requests.post(self.metrics_url_template_via_citations, 
                        data="citation_ids="+id, 
                        headers=headers)

        # extract the metrics
        try:
            data = r.json() 
            metrics_dict = self._extract_metrics_for_via_citation_call(data)
        except socket.timeout, e:  # can apparently be thrown here
            self.logger.info(u"%s Provider timed out *after* GET in socket" %(self.provider_name))        
            raise ProviderTimeout("Provider timed out *after* GET in socket", e)        
        except (AttributeError, TypeError, ValueError):  # ValueError includes simplejson.decoder.JSONDecodeError
            # expected response if nothing found
            metrics_dict = {}

        return metrics_dict



    def metrics(self, 
            aliases,
            provider_url_template=None, 
            cache_enabled=True):

        id = self.get_best_id(aliases)

        # Only lookup metrics for items with appropriate ids
        if not id:
            #self.logger.debug(u"%s not checking metrics, no relevant alias" % (self.provider_name))
            return {}

        metrics = {}
        new_metrics = self.get_metrics_for_id(id, self.metrics_url_template_via_fetch, cache_enabled, 
                extract_metrics_method=self._extract_metrics_via_fetch)
        if new_metrics:
            metrics.update(new_metrics)
        new_metrics = self.get_metrics_for_via_citation_call(id)
        if new_metrics:
            metrics.update(new_metrics)

        metrics_and_drilldown = {}
        for metric_name in metrics:
            drilldown_url = self.provenance_url(metric_name, aliases)
            metrics_and_drilldown[metric_name] = (metrics[metric_name], drilldown_url)

        return metrics_and_drilldown  




