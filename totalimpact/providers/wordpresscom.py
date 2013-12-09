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
    metrics_url_template = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    metrics_url_template_views = "http://stats.wordpress.com/csv.php?api_key=%s&blog_uri=%s&table=views&days=-1&format=json&summarize=1"
    provenance_url_template = "%s"

    static_meta_dict = {
        "subscribers": {
            "display_name": "subscribers",
            "provider": "WordPress.com",
            "provider_url": "http://wordpress.com",
            "description": "The number of people who receive emails about new posts on this blog.",
            "icon": "https://wordpress.com/favicon.ico",
        },
        "views": {
            "display_name": "views",
            "provider": "WordPress.com",
            "provider_url": "http://wordpress.com",
            "description": "The number of times a blog post has been viewed.",
            "icon": "https://wordpress.com/favicon.ico",
        }
    }     

    def __init__(self):
        super(Wordpresscom, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return "blog"==namespace

    # overriding default because overriding member_items method
    @property
    def provides_members(self):
        return True

    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    # overriding default because overriding aliases method
    @property
    def provides_biblio(self):
        return True


    def blog_url(self, nid):
        return re.sub("http(s?)://", "", nid.lower())

    #override because need to break up id
    def _get_templated_url(self, template, nid, method=None):
        blog_url = self.url_from_nid(nid)
        if method in ["metrics", "biblio"]:
            blog_url = self.blog_url(blog_url)
        url = template % (blog_url)
        return(url)


    # overriding
    def member_items(self, 
            input_dict, 
            provider_url_template=None, 
            cache_enabled=True):

        members = []

        if "apiKey" in input_dict:
            api_key = input_dict["apiKey"]
        else:
            api_key = None

        if "blogUrl" in input_dict:
            blog_url = input_dict["blogUrl"]
        else:
            blog_url = None

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
                        "blog_url": blog_url_for_blog_post_urls, 
                        "api_key": api_key
                        }
                members += [("blog_post_CONFIDENTIAL", json.dumps(blog_post_nid))] 


        if blog_url:
            blog_nid = {"api_key": api_key, "url": blog_url}
            members += [("blog", json.dumps(blog_nid))]

            # import top blog posts
            blog_url = blog_url
            for post_url in topsy.Topsy().top_tweeted_urls(blog_url, number_to_return=10):
                blog_post_nid = {   
                        "post_url": post_url, 
                        "blog_url": blog_url, 
                        "api_key": api_key
                        }
                members += [("blog_post_CONFIDENTIAL", json.dumps(blog_post_nid))] 

        return (members)


    def url_from_nid(self, nid):
        return json.loads(nid)["url"]    
  
    def api_key_from_nid(self, nid):
        return json.loads(nid)["api_key"]    

    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        new_aliases = []

        for alias in aliases:
            (namespace, nid) = alias
            if namespace=="blog":
                new_alias = ("url", self.url_from_nid(nid))
                if new_alias not in aliases:
                    new_aliases += [new_alias]

        return new_aliases


    def biblio(self, 
            aliases,
            provider_url_template=None,
            cache_enabled=True):

        blog_nid = self.get_best_id(aliases)
        biblio_dict = {}
        biblio_dict["url"] = self.url_from_nid(blog_nid)
        biblio_dict["account"] = self.url_from_nid(blog_nid)
        biblio_dict["is_account"] = True  # special key to tell webapp to render as genre heading

        return biblio_dict



    def _extract_metrics(self, page, status_code=200, id=None):
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

        api_key = self.api_key_from_nid(id)
        if api_key:
            blog_url = self.url_from_nid(id)
            url = self.metrics_url_template_views % (api_key, blog_url)
            response = self.http_get(url)
            try:
                data = json.loads(response.text)
                metrics_dict["wordpresscom:views"] = data["views"] 
            except ValueError:
                pass

        return metrics_dict


