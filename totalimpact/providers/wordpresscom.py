from totalimpact.providers import provider
from totalimpact.providers import topsy
from totalimpact.providers import webpage
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import json, os, re

import logging
logger = logging.getLogger('ti.providers.wordpresscom')

class Wordpresscom(Provider):  

    example_id = ("blog", "http://blog.impactstory.org")

    url = "http://wordpress.com"
    descr = "A blog web hosting service provider owned by Automattic, and powered by the open source WordPress software."
    biblio_url_template = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    aliases_url_template = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    metrics_url_template_public = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    metrics_url_template_comments = "https://public-api.wordpress.com/rest/v1/sites/%s/comments?pretty=1"
    metrics_url_template_wordpress_blog_views = "http://stats.wordpress.com/csv.php?api_key=%s&blog_uri=%s&table=views&days=-1&format=json&summarize=1"
    metrics_url_template_wordpress_post_views = "http://stats.wordpress.com/csv.php?api_key=%s&blog_uri=%s&table=views&days=-1&format=json&summarize=1&table=postviews&post_id=%s"
    metrics_url_template_wordpress_post_comments = "https://public-api.wordpress.com/rest/v1/sites/%s/posts/%s?pretty=1"
    provenance_url_template = "%s"

    static_meta_dict = {
        "subscribers": {
            "display_name": "subscribers",
            "provider": "WordPress.com",
            "provider_url": "http://wordpress.com",
            "description": "The number of people who receive emails about new posts on this blog",
            "icon": "https://wordpress.com/favicon.ico",
        },
        "views": {
            "display_name": "views",
            "provider": "WordPress.com",
            "provider_url": "http://wordpress.com",
            "description": "The number of times a blog post has been viewed",
            "icon": "https://wordpress.com/favicon.ico",
        },
        "comments": {
            "display_name": "comments",
            "provider": "WordPress.com",
            "provider_url": "http://wordpress.com",
            "description": "The number of comments on a blog post",
            "icon": "https://wordpress.com/favicon.ico",
        }
    }     

    def __init__(self):
        super(Wordpresscom, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return namespace in ["blog", "blog_post"]

    # overriding default because overriding member_items method
    @property
    def provides_members(self):
        return True

    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    # overriding default because overriding biblio method
    @property
    def provides_biblio(self):
        return True

    # overriding default because overriding metrics method
    @property
    def provides_metrics(self):
        return True

    # overriding
    def uses_analytics_credentials(self, method_name):
        if method_name == "metrics":
            return True
        else:
            return False



    #override because need to break strip http
    def _get_templated_url(self, template, nid, method=None):
        if method in ["metrics", "biblio", "aliases"]:
            nid = provider.strip_leading_http(nid).lower()
        url = template % (nid)
        return(url)


    # overriding
    def member_items(self, 
            input_dict, 
            provider_url_template=None, 
            cache_enabled=True):

        members = []

        if "blogUrl" in input_dict:
            blog_url = input_dict["blogUrl"]
        else:
            blog_url = None

        if blog_url:
            members += [("blog", blog_url)]

            # import top blog posts
            for post_url in topsy.Topsy().top_tweeted_urls(blog_url, number_to_return=10):
                blog_post_nid = {   
                        "post_url": post_url, 
                        "blog_url": blog_url
                        }
                members += [("blog_post", json.dumps(blog_post_nid))] 


        # handle individual blog posts
        if "blog_post_urls" in input_dict:
            members_as_webpages = webpage.Webpage().member_items(input_dict["blog_post_urls"])
            for (url_namespace, post_url) in members_as_webpages:
                if blog_url:
                    blog_url_for_blog_post_urls = blog_url
                else:
                    blog_url_for_blog_post_urls = "http://"+provider.strip_leading_http(post_url).split("/", 1)[0]
                blog_post_nid = {   
                        "post_url": post_url, 
                        "blog_url": blog_url_for_blog_post_urls 
                        }
                members += [("blog_post", json.dumps(blog_post_nid))] 

        return (members)
  

    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        new_aliases = []
        if not provider_url_template:
            provider_url_template = self.aliases_url_template

        for alias in aliases:
            (namespace, nid) = alias
            if namespace=="blog":
                new_alias = ("url", nid)
                if new_alias not in aliases:
                    new_aliases += [new_alias]

                url = self._get_templated_url(provider_url_template, nid, "aliases")

                # try to get a response from the data provider        
                response = self.http_get(url, cache_enabled=cache_enabled)

                if (response.status_code == 200) and ("ID" in response.text):
                    dict_of_keylists = {
                            'wordpress_blog_id' : ['ID']
                        }
                    aliases_dict = provider._extract_from_json(response.text, dict_of_keylists)
                    new_alias = ("wordpress_blog_id", str(aliases_dict["wordpress_blog_id"]))
                    if new_alias not in aliases:
                        new_aliases += [new_alias]

        return new_aliases


    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "blog" in aliases_dict:
            id = aliases_dict["blog"][0]

        # Only lookup biblio for items with appropriate ids
        if not id:
            #self.logger.debug(u"%s not checking biblio, no relevant alias" % (self.provider_name))
            return None

        if not provider_url_template:
            provider_url_template = self.biblio_url_template

        self.logger.debug(u"%s getting biblio for %s" % (self.provider_name, id))

        # set up stuff that is true for all blogs, wordpress and not
        biblio_dict = {}
        biblio_dict["url"] = id
        biblio_dict["account"] = provider.strip_leading_http(id)
        biblio_dict["is_account"] = True  # special key to tell webapp to render as genre heading

        # now add things that are true just for wordpress blogs

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        url = self._get_templated_url(provider_url_template, id, "biblio")

        # try to get a response from the data provider        
        response = self.http_get(url, cache_enabled=cache_enabled)

        if (response.status_code == 200) and ("name" in response.text):
            biblio_dict["hosting_platform"] = "wordpress.com"
            try:
                biblio_dict.update(self._extract_biblio(response.text, id))
            except (AttributeError, TypeError):
                pass

        return biblio_dict


    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['name'],
            'description' : ['description']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists)
        return biblio_dict   


    def wordpress_post_id_from_nid(self, nid):
        try:
            return json.loads(nid)["wordpress_post_id"]    
        except (KeyError, ValueError):
            return None

    def blog_url_from_nid(self, nid):
        try:
            return json.loads(nid)["blog_url"]    
        except (KeyError, ValueError):
            return None


    # default method; providers can override    
    def provenance_url(self, metric_name, aliases):
        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "url" in aliases_dict:
            return aliases_dict["url"][0]
        else:
            return self.get_best_id(aliases)


    def metrics(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True, 
            analytics_credentials=None):

        metrics = {}

        aliases_dict = provider.alias_dict_from_tuples(aliases)
        if "blog" in aliases_dict:
            blog_url = aliases_dict["blog"][0]

            url_override = self.metrics_url_template_public % (provider.strip_leading_http(blog_url).lower())

            new_metrics = self.get_metrics_for_id(blog_url,
                                cache_enabled=cache_enabled, 
                                extract_metrics_method=self._extract_metrics_subscribers,
                                url_override=url_override)
            metrics.update(new_metrics)

        if "wordpress_blog_id" in aliases_dict:
            wordpress_blog_id = aliases_dict["wordpress_blog_id"][0]

            url_override = self.metrics_url_template_comments % wordpress_blog_id

            new_metrics = self.get_metrics_for_id(blog_url,
                                cache_enabled=cache_enabled, 
                                extract_metrics_method=self._extract_metrics_blog_comments,
                                url_override=url_override)
            metrics.update(new_metrics)


        if ("blog" in aliases_dict) and analytics_credentials:
            blog_url = aliases_dict["blog"][0]
            api_key = analytics_credentials["wordpress_api_key"]

            url_override = self.metrics_url_template_wordpress_blog_views % (api_key, provider.strip_leading_http(blog_url).lower())

            new_metrics = self.get_metrics_for_id(blog_url,
                                cache_enabled=cache_enabled, 
                                extract_metrics_method=self._extract_metrics_blog_views,
                                url_override=url_override)

            metrics.update(new_metrics)

        if ("wordpress_blog_post" in aliases_dict):
            nid = aliases_dict["wordpress_blog_post"][0]
            post_id = self.wordpress_post_id_from_nid(nid)
            blog_url = self.blog_url_from_nid(nid)

            url_override = self.metrics_url_template_wordpress_post_comments % (provider.strip_leading_http(blog_url).lower(), post_id)
            new_metrics = self.get_metrics_for_id(post_id,
                                cache_enabled=cache_enabled, 
                                extract_metrics_method=self._extract_metrics_post_comments,
                                url_override=url_override)
            metrics.update(new_metrics)

            if analytics_credentials:
                api_key = analytics_credentials["wordpress_api_key"]

                url_override = self.metrics_url_template_wordpress_post_views % (api_key, provider.strip_leading_http(blog_url).lower(), post_id)
                new_metrics = self.get_metrics_for_id(blog_url,
                                    cache_enabled=cache_enabled, 
                                    extract_metrics_method=self._extract_metrics_blog_views,
                                    url_override=url_override)
                metrics.update(new_metrics)


        metrics_and_drilldown = {}
        for metric_name in metrics:
            drilldown_url = self.provenance_url(metric_name, aliases)
            metrics_and_drilldown[metric_name] = (metrics[metric_name], drilldown_url)

        return metrics_and_drilldown 



    def _extract_metrics_subscribers(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "is_private" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'wordpresscom:subscribers' : ['subscribers_count']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)
        return metrics_dict


    def _extract_metrics_blog_views(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "views" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'wordpresscom:views' : ['views']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)        
        return metrics_dict


    def _extract_metrics_blog_comments(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "found" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'wordpresscom:comments' : ['found']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)        
        return metrics_dict


    def _extract_metrics_post_comments(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "comment_count" in page:
            raise ProviderContentMalformedError

        dict_of_keylists = {
            'wordpresscom:comments' : ['comment_count']
        }

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)        
        return metrics_dict

