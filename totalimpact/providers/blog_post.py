from totalimpact.providers import provider
from totalimpact.providers import webpage
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderServerError

import json, os, re

import logging
logger = logging.getLogger('ti.providers.blog_post')

class Blog_Post(Provider):  

    example_id = ('blog_post', '{"post_url": "http://researchremix.wordpress.com/2012/04/17/elsevier-agrees/", "blog_url": "researchremix.wordpress.com"}')
    metrics_url_template = "http://stats.wordpress.com/csv.php?api_key=%s&blog_uri=%s&table=views&days=-1&format=json&summarize=1&table=postviews&post_id=%s"
    biblio_url_template = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    metrics_url_template_wordpress_site = "https://public-api.wordpress.com/rest/v1/sites/%s/?pretty=1"
    metrics_url_template_wordpress_post = "https://public-api.wordpress.com/rest/v1/sites/%s/posts/slug:%s?pretty=1"
    provenance_url_template = "%s"

    static_meta_dict = {}


    def __init__(self):
        super(Blog_Post, self).__init__()


    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return "blog_post" in namespace


    def get_best_id(self, aliases):
        aliases_dict = provider.alias_dict_from_tuples(aliases)

        # go through in preferred order
        for key in ["wordpress_blog_post", "blog_post", "url"]:
            if key in aliases_dict:
                nid = aliases_dict[key][0]
                return nid
        return None


    # overriding default because overriding aliases method
    @property
    def provides_aliases(self):
        return True

    # overriding default because overriding aliases method
    @property
    def provides_biblio(self):
        return True


    #override because need to break up id
    def _get_templated_url(self, template, nid, method=None):
        url = None
        if method=="biblio":
            nid = provider.strip_leading_http(nid).lower()
            url = template % (nid)
        elif method=="provenance":
            url = self.post_url_from_nid(nid)
        else:
            url = template % (nid)
        return(url)


    def post_url_from_nid(self, nid):
        try:
            return json.loads(nid)["post_url"]    
        except (KeyError, ValueError):
            return None

    def blog_url_from_nid(self, nid):
        try:
            return json.loads(nid)["blog_url"]    
        except (KeyError, ValueError):
            return None


    def wordpress_post_id_from_nid(self, nid):
        try:
            return json.loads(nid)["wordpress_post_id"]    
        except (KeyError, ValueError):
            return None


    # overriding
    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        aliases_dict = provider.alias_dict_from_tuples(aliases)
        new_aliases = []

        if "blog_post" in aliases_dict:
            nid = aliases_dict["blog_post"][0]
            post_url = self.post_url_from_nid(nid)

            # add url as alias if not already there
            new_alias = ("url", post_url)
            if new_alias not in aliases:
                new_aliases += [new_alias]

            # now add the wordpress alias info if it isn't already there
            if not "wordpress_blog_post" in aliases_dict:
                blog_url = provider.strip_leading_http(self.blog_url_from_nid(nid))
                wordpress_blog_api_url = self.metrics_url_template_wordpress_site % blog_url

                response = self.http_get(wordpress_blog_api_url)
                if "name" in response.text:
                    # it is a wordpress blog, so now get its wordpress post ID
                    if post_url.endswith("/"):
                        post_url = post_url[:-1]
                    post_end_slug = post_url.rsplit("/", 1)[1]

                    wordpress_post_api_url = self.metrics_url_template_wordpress_post %(blog_url, post_end_slug)
                    response = self.http_get(wordpress_post_api_url)
                    if "ID" in response.text:
                        wordpress_post_id = json.loads(response.text)["ID"]
                        nid_as_dict = json.loads(nid)
                        nid_as_dict.update({"wordpress_post_id": wordpress_post_id})
                        new_aliases += [("wordpress_blog_post", json.dumps(nid_as_dict))]

        return new_aliases



    # overriding
    def biblio(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True): 
        logger.info(u"calling webpage to handle aliases")

        nid = self.get_best_id(aliases)
        aliases_dict = provider.alias_dict_from_tuples(aliases)   
        nid = aliases_dict["blog_post"][0]
        post_url = self.post_url_from_nid(nid)
        blog_url = self.blog_url_from_nid(nid)

        biblio_dict = webpage.Webpage().biblio([("url", post_url)], provider_url_template, cache_enabled) 
        biblio_dict["url"] = post_url
        biblio_dict["account"] = provider.strip_leading_http(self.blog_url_from_nid(nid))
        if ("title" in biblio_dict) and ("|" in biblio_dict["title"]):
            (title, blog_title) = biblio_dict["title"].rsplit("|", 1)
            biblio_dict["title"] = title.strip()
            biblio_dict["blog_title"] = blog_title.strip()

        # try to get a response from wordpress.com
        url = self._get_templated_url(self.biblio_url_template, blog_url, "biblio")           
        response = self.http_get(url, cache_enabled=cache_enabled)
        if (response.status_code == 200) and ("name" in response.text):
            biblio_dict["hosting_platform"] = "wordpress.com"

        # in the future could get date posted from these sorts of calls:
        # https://public-api.wordpress.com/rest/v1/sites/blog.impactstory.org/posts/slug:link-your-figshare-and-impactstory-strips

        return biblio_dict



