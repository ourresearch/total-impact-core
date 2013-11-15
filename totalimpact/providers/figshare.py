from totalimpact.providers import provider
from totalimpact.providers import crossref
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import re

import logging
logger = logging.getLogger('ti.providers.figshare')

class Figshare(Provider):  

    example_id = ("doi", "10.6084/m9.figshare.92393")

    url = "http://figshare.com"
    descr = "Make all of your research outputs sharable, citable and visible in the browser for free."
    biblio_url_template = "http://api.figshare.com/v1/articles/%s"
    aliases_url_template = "http://api.figshare.com/v1/articles/%s"
    metrics_url_template = "http://api.figshare.com/v1/articles/%s"
    provenance_url_template = "http://dx.doi.org/%s"
    member_items_url_template = "http://api.figshare.com/v1/authors/%s?page=%s"


    static_meta_dict = {
        "shares": {
            "display_name": "shares",
            "provider": "figshare",
            "provider_url": "http://figshare.com",
            "description": "The number of times this has been shared",
            "icon": "http://figshare.com/static/img/favicon.png",
        },
        "downloads": {
            "display_name": "downloads",
            "provider": "figshare",
            "provider_url": "http://figshare.com",
            "description": "The number of times this has been downloaded",
            "icon": "http://figshare.com/static/img/favicon.png",
            },
        "views": {
            "display_name": "views",
            "provider": "figshare",
            "provider_url": "http://figshare.com",
            "description": "The number of times this item has been viewed",
            "icon": "http://figshare.com/static/img/favicon.png",
            }
    }     

    def __init__(self):
        super(Figshare, self).__init__()
        self.crossref = crossref.Crossref()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        is_figshare_doi = (namespace == "doi") and (".figshare." in nid.lower())
        return is_figshare_doi

    @property
    def provides_aliases(self):
         return True

    @property
    def provides_biblio(self):
         return True

    @property
    def provides_members(self):
         return True

    def get_figshare_userid_from_author_url(self, url):
        match = re.findall("figshare.com\/authors\/.*?\/(\d+)", url)
        return match[0]


    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):  
        logger.info(u"calling crossref to handle aliases")
        return self.crossref.aliases(aliases, provider_url_template, cache_enabled)          


    def biblio(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):  
        logger.info(u"calling crossref to handle aliases")
        return self.crossref.biblio(aliases, provider_url_template, cache_enabled) 


    def _extract_figshare_record(self, page, id):
        data = provider._load_json(page)
        if not data:
            return {}
        item = data["items"][0]
        if str(item["article_id"]) in id:
            return item
        else:
            return {}


    def _extract_metrics(self, page, status_code=200, id=None):
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        dict_of_keylists = {
            'figshare:shares' : ['shares'],
            'figshare:downloads' : ['downloads'],
            'figshare:views' : ['views']
        }
        item = self._extract_figshare_record(page, id)
        metrics_dict = provider._extract_from_data_dict(item, dict_of_keylists)
        return metrics_dict


    def _extract_members(self, page, query_string=None): 
        data = provider._load_json(page)        
        dois = [item["DOI"].replace("http://dx.doi.org/", "") for item in data["items"]]
        doi_aliases = [("doi", doi) for doi in dois]
        return(doi_aliases)


    # default method; providers can override
    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        if not self.provides_members:
            raise NotImplementedError()

        self.logger.debug(u"%s getting member_items for %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        figshare_userid = self.get_figshare_userid_from_author_url(query_string)
        next_page = 1
        members = []
        while next_page:

            url = provider_url_template % (figshare_userid, next_page)
            
            # try to get a response from the data provider  
            response = self.http_get(url, cache_enabled=cache_enabled)

            if response.status_code != 200:
                self.logger.info(u"%s status_code=%i" 
                    % (self.provider_name, response.status_code))            
                if response.status_code == 404:
                    raise ProviderItemNotFoundError
                elif response.status_code == 303: #redirect
                    pass                
                else:
                    self._get_error(response.status_code, response)

            # extract the member ids
            number_of_items_per_page = 10 #figshare default
            try:
                page = response.text
                data = provider._load_json(page)
                if data["items_found"] > next_page*number_of_items_per_page:
                    next_page += 1
                else:
                    next_page = None
                members += self._extract_members(page, query_string)
            except (AttributeError, TypeError):
                next_page = None

        return(members)


