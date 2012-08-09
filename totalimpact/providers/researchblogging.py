from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson
import re

import logging
logger = logging.getLogger('providers.researchblogging')

class Researchblogging(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://researchblogging.org/"
    descr = "ResearchBlogging.org to make it easy to find your serious posts about academic research"
    metrics_url_template = "http://researchblogging.org/post-search/list?search_text=%s"
    provenance_url_template = "http://researchblogging.org/post-search/list?search_text=%s"
    blog_html_template = re.compile('<div class="articleData"')

    static_meta_dict =  {
        "blogs": {
            "display_name": "blogs",
            "provider": "Research Blogging",
            "provider_url": "http://researchblogging.org/",
            "description": "Number of users who have blogged this item through Research Blogging.",
            "icon": "http://researchblogging.org/favicon.ico" ,
        }    
    }
    

    def __init__(self):
        super(Researchblogging, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)


    def _extract_metrics(self, page, status_code=200, id=None):

        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "views</li>" in page:
            raise ProviderContentMalformedError

        count = len(self.blog_html_template.findall(page))

        if count:
            metrics_dict = {'researchblogging:blogs': count}
        else:
            metrics_dict = {}

        return metrics_dict



