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


    #override because need to break strip http
    def _get_templated_url(self, template, nid, method=None):
        if method in ["metrics", "biblio"]:
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

        for alias in aliases:
            (namespace, nid) = alias
            if namespace=="blog":
                new_alias = ("url", nid)
                if new_alias not in aliases:
                    new_aliases += [new_alias]

        return new_aliases


    # overridding
    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug(u"%s getting biblio for %s" % (self.provider_name, id))

        # set up stuff that is true for all blogs, wordpress and not
        biblio_dict = {}
        biblio_dict["url"] = id
        biblio_dict["account"] = id
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

        # api_key = self.api_key_from_nid(id)
        # if api_key:
        #     blog_url = self.url_from_nid(id)
        #     url = self.metrics_url_template_views % (api_key, blog_url)
        #     response = self.http_get(url)
        #     try:
        #         data = json.loads(response.text)
        #         metrics_dict["wordpresscom:views"] = data["views"] 
        #     except ValueError:
        #         pass

        return metrics_dict


