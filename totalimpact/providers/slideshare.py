from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderItemNotFoundError, ProviderRateLimitError

import simplejson, urllib, time, hashlib, re, os
from xml.dom import minidom 
from xml.parsers.expat import ExpatError

import logging
logger = logging.getLogger('ti.providers.slideshare')

class Slideshare(Provider):  

    example_id = ("url", "http://www.slideshare.net/cavlec")
    url = "http://www.slideshare.net/"
    descr = "The best way to share presentations, documents and professional videos."

    member_items_url_template = "https://www.slideshare.net/api/2/get_slideshows_by_user?api_key=" + os.environ["SLIDESHARE_KEY"] + "&detailed=1&ts=%s&hash=%s&username_for=%s"
    everything_url_template = "https://www.slideshare.net/api/2/get_slideshow?api_key=" + os.environ["SLIDESHARE_KEY"] + "&detailed=1&ts=%s&hash=%s&slideshow_url=%s"
    biblio_url_template = everything_url_template
    aliases_url_template = everything_url_template
    metrics_url_template = everything_url_template
    provenance_url_template = "%s"

    sanity_check_re = re.compile("<User")

    static_meta_dict = {
        "downloads": {
            "display_name": "downloads",
            "provider": "SlideShare",
            "provider_url": "http://www.slideshare.net/",
            "description": "The number of times the presentation has been downloaded",
            "icon": "http://www.slideshare.net/favicon.ico" ,
        },    
        "favorites": {
            "display_name": "favorites",
            "provider": "SlideShare",
            "provider_url": "http://www.slideshare.net/",
            "description": "The number of times the presentation has been favorited",
            "icon": "http://www.slideshare.net/favicon.ico" ,
        },    
        "comments": {
            "display_name": "comments",
            "provider": "SlideShare",
            "provider_url": "http://www.slideshare.net/",
            "description": "The number of comments the presentation has received",
            "icon": "http://www.slideshare.net/favicon.ico" ,
        },    
        "views": {
            "display_name": "views",
            "provider": "SlideShare",
            "provider_url": "http://www.slideshare.net/",
            "description": "The number of times the presentation has been viewed",
            "icon": "http://www.slideshare.net/favicon.ico" ,
        }    
    }


    def __init__(self):
        super(Slideshare, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        relevant = ((namespace=="url") and re.match(".+slideshare.net/.+/.+", nid))
        return(relevant)

    #override because need to break up id
    def _get_templated_url(self, template, id, method=None):
        if method=="provenance":
            return template %id
            
        ts = time.time()
        hash_combo = hashlib.sha1(os.environ["SLIDESHARE_SECRET"] + str(ts)).hexdigest()
        complete_url = template %(ts, hash_combo, id)
        return(complete_url)

    def _sanity_check_page(self, page):
        if not self.sanity_check_re.search(page):
            if ("User Not Found" in page):
                raise ProviderItemNotFoundError
            elif ("Account Exceeded Daily Limit" in page):
                logger.info(u"Exceeded api limit for provider {provider}".format(
                    provider=self.provider_name))
                raise ProviderRateLimitError("Exceeded api limit for provider {provider}".format(
                    provider=self.provider_name))
            else:
                raise ProviderContentMalformedError
        return True

    def _extract_members(self, page, account_name):
        try:
            doc = minidom.parseString(page.strip().encode('utf-8'))
        except ExpatError:
            raise ProviderContentMalformedError

        self._sanity_check_page(page)

        urls = doc.getElementsByTagName("URL")

        members = [("url", url.firstChild.data) for url in list(set(urls))]

        # also add the slideshare account
        slideshare_account_url = u"https://www.slideshare.net/{account_name}".format(
            account_name=account_name)
        members += [("url", slideshare_account_url)]

        return(members)

    def _extract_biblio(self, page, id=None):
        dict_of_keylists = {
            'title' : ['Slideshow', 'Title'],
            'username' : ['Slideshow', 'Username'],
            'created' : ['Slideshow', 'Created'],
        }
        self._sanity_check_page(page)

        biblio_dict = provider._extract_from_xml(page, dict_of_keylists)
        biblio_dict["repository"] = "Slideshare"
        try:
            biblio_dict["year"] = biblio_dict["created"][0:4]
        except KeyError:
            pass
        
        return biblio_dict    
       
    def _extract_aliases(self, page, id=None):
        dict_of_keylists = {
            'title' : ['Slideshow', 'Title']
        }
        self._sanity_check_page(page)

        aliases_dict = provider._extract_from_xml(page, dict_of_keylists)
        if aliases_dict:
            aliases_list = [(namespace, nid) for (namespace, nid) in aliases_dict.iteritems()]
        else:
            aliases_list = []
        return aliases_list


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))
        self._sanity_check_page(page)

        dict_of_keylists = {
            'slideshare:downloads' : ['Slideshow', 'NumDownloads'],
            'slideshare:views' : ['Slideshow', 'NumViews'],
            'slideshare:comments' : ['Slideshow', 'NumComments'],
            'slideshare:favorites' : ['Slideshow', 'NumFavorites'],
        }

        metrics_dict = provider._extract_from_xml(page, dict_of_keylists)
        for mykey in metrics_dict:
            metrics_dict[mykey] = int( metrics_dict[mykey])
        return metrics_dict

